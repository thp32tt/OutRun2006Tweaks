param(
    [Parameter(Mandatory=$true)]
    [string]$SessionDir
)

$ErrorActionPreference='Stop'
if(!(Test-Path $SessionDir)){throw "Session directory not found: $SessionDir"}

function Read-AllText([string]$name){
    $p=Join-Path $SessionDir $name
    if(Test-Path $p){return (Get-Content $p -Raw -ErrorAction SilentlyContinue)}
    return ''
}

function Get-LastRegexMatch([string]$text,[string]$pattern){
    $matches=[regex]::Matches($text,$pattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if($matches.Count -eq 0){return $null}
    return $matches[$matches.Count-1]
}

$session=@{}
$manifestPath=Join-Path $SessionDir 'session_manifest.json'
if(Test-Path $manifestPath){
    try{$session=Get-Content $manifestPath -Raw|ConvertFrom-Json}catch{$session=@{}}
}

$gameLog=Read-AllText 'OutRun2006Tweaks.log'
$dxvkLog=Read-AllText 'OR2006C2C_d3d9.log'
$hostLog=(Read-AllText 'outrun-vr-host-v3.log')+"\n"+(Read-AllText 'outrun-vr-host-pipeline.log')
$combined=$gameLog+"\n"+$dxvkLog+"\n"+$hostLog

$provider='UNKNOWN'
if($dxvkLog -match 'DXVK:\s*v([0-9\.]+)'){$provider='DXVK '+$matches[1]}
elseif($gameLog -match 'native D3D9Ex zero-copy transport'){$provider='NATIVE_D3D9EX'}
elseif($gameLog -match 'plain IDirect3DDevice9 detected'){$provider='PLAIN_D3D9'}

$sbsFallback=($combined -match 'transport=SBS Desktop Duplication' -or
    $combined -match 'SBS/Desktop Duplication remains active' -or
    $combined -match 'keeping SBS/Desktop Duplication fallback')
$plainD3D9=($combined -match 'plain IDirect3DDevice9 detected')
$sharedProbeFailed=($combined -match 'shared verification texture creation/upload failed')
$driverSeatCount=([regex]::Matches($gameLog,'VR DRIVER SEAT CAMERA:')).Count
$crashEvidence=($combined -match '(?im)\b(crash|unhandled exception|access violation|fatal error)\b')
$whiteScreenEvidence=($combined -match '(?im)white screen|white-screen|startup white')

$directFrames=0
$directFallbacks=0
$fenceTimeout=0
$m=Get-LastRegexMatch $gameLog 'direct\[frames=(\d+),fallbacks=(\d+),fenceTimeout=(\d+)\]'
if($m){
    $directFrames=[int64]$m.Groups[1].Value
    $directFallbacks=[int64]$m.Groups[2].Value
    $fenceTimeout=[int64]$m.Groups[3].Value
}

$frameIntervals=@()
foreach($m2 in [regex]::Matches($hostLog,'xrFrameIntervalMs=([0-9\.]+)')){
    $v=0.0
    if([double]::TryParse($m2.Groups[1].Value,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$v)){
        if($v -gt 0 -and $v -lt 1000){$frameIntervals+=$v}
    }
}
$avgFrameMs=$null
$approxHz=$null
if($frameIntervals.Count -gt 0){
    $avgFrameMs=($frameIntervals|Measure-Object -Average).Average
    if($avgFrameMs -gt 0){$approxHz=1000.0/$avgFrameMs}
}

$perfSpikeRows=@()
$perfSpikePattern='VR R32 FRAME SPIKE: frameUs=(\d+) baselineUs=(\d+) presentUs=(\d+).*?draws=(\d+),primitives=(\d+),triangles=(\d+),indexed=(\d+),up=(\d+),alphaBlend=(\d+),alphaBlendPrimitives=(\d+),alphaTest=(\d+),particleLikeDraws=(\d+),particleLikePrimitives=(\d+),effectUnknown=(\d+).*?fenceWaitUs=(\d+),fencePolls=(\d+)'
foreach($spike in [regex]::Matches($gameLog,$perfSpikePattern)){
    $perfSpikeRows += [pscustomobject]@{
        FrameUs=[int64]$spike.Groups[1].Value
        BaselineUs=[int64]$spike.Groups[2].Value
        PresentUs=[int64]$spike.Groups[3].Value
        Draws=[int64]$spike.Groups[4].Value
        Primitives=[int64]$spike.Groups[5].Value
        Triangles=[int64]$spike.Groups[6].Value
        IndexedDraws=[int64]$spike.Groups[7].Value
        UpDraws=[int64]$spike.Groups[8].Value
        AlphaBlendDraws=[int64]$spike.Groups[9].Value
        AlphaBlendPrimitives=[int64]$spike.Groups[10].Value
        AlphaTestDraws=[int64]$spike.Groups[11].Value
        ParticleLikeDraws=[int64]$spike.Groups[12].Value
        ParticleLikePrimitives=[int64]$spike.Groups[13].Value
        EffectUnknownDraws=[int64]$spike.Groups[14].Value
        FenceWaitUs=[int64]$spike.Groups[15].Value
        FencePolls=[int64]$spike.Groups[16].Value
    }
}
$perfSpikeCount=$perfSpikeRows.Count
$perfSpikeMaxFrameUs=0
$perfSpikeMaxDraws=0
$perfSpikeMaxPrimitives=0
$perfSpikeMaxParticleLikeDraws=0
$perfSpikeMaxParticleLikePrimitives=0
$perfSpikeMaxFenceWaitUs=0
if($perfSpikeCount -gt 0){
    $perfSpikeMaxFrameUs=($perfSpikeRows|Measure-Object FrameUs -Maximum).Maximum
    $perfSpikeMaxDraws=($perfSpikeRows|Measure-Object Draws -Maximum).Maximum
    $perfSpikeMaxPrimitives=($perfSpikeRows|Measure-Object Primitives -Maximum).Maximum
    $perfSpikeMaxParticleLikeDraws=($perfSpikeRows|Measure-Object ParticleLikeDraws -Maximum).Maximum
    $perfSpikeMaxParticleLikePrimitives=($perfSpikeRows|Measure-Object ParticleLikePrimitives -Maximum).Maximum
    $perfSpikeMaxFenceWaitUs=($perfSpikeRows|Measure-Object FenceWaitUs -Maximum).Maximum
    $perfSpikeRows|Export-Csv (Join-Path $SessionDir 'PERFORMANCE_SPIKES.csv') -NoTypeInformation -Encoding UTF8
}

# The original rank CALLs can run without any actual R57 projected draw.
# A no-red-flag verdict is false in that case; report the missing ownership.
$rankTrace=Read-AllText 'HUD_TRACE_SUMMARY.txt'
$rankProducerObserved=($rankTrace -match 'RankMarker/sub_4BAD20')
$projectedSemantic=-1
$projectedSummary=Get-LastRegexMatch $gameLog 'projected\[semantic=(\d+),missingPayload='
if($projectedSummary){$projectedSemantic=[int64]$projectedSummary.Groups[1].Value}
$rankProjectionNotReached=($rankProducerObserved -and $projectedSemantic -eq 0)
# Actual rank/DispRank/GOAL eye and D3DXSprite outcomes must not be
# confused with an attempted original producer or an R57 projection build.
# New outcome evidence is opt-in: older ZIPs without these logs stay UNKNOWN,
# not retrospectively marked HMD success or failure.
$exactHudProducer='(?:RANK_MARKER_SPRANI|RANK_MARKER_CLIP|DISPLAY_RANK_FIRST|DISPRANK_KIND0_CLIP|GOAL_TIME_HELPER_020|GOAL_TIME_HELPER_150|OUTRUN_RESULT_PROGRESS|OUTRUN_STAGE_PRINT)'
$hudStereoEyeRejected=[regex]::IsMatch($gameLog,
    'VR R62 FIXEDFN KIND0:[^\r\n]*producer='+$exactHudProducer+'[^\r\n]*stereoAccepted=0(?:\s|$)')
$hudD3dxFlushFailed=[regex]::IsMatch($gameLog,
    'VR R64 D3DX ISOLATE RESTORED:[^\r\n]*producer='+$exactHudProducer+'[^\r\n]*flushSucceeded=0(?:\s|$)')


$gameDllIdentity=Read-AllText 'GAME_DLL_IDENTITY.txt'
$gameDllMismatch=($gameDllIdentity -match '(?m)^installedMatchesSelected=False\s*$')
$flags=@()
if($sbsFallback){$flags+='SBS_DESKTOP_DUP_FALLBACK'}
if($plainD3D9){$flags+='PLAIN_D3D9_PROVIDER'}
if($sharedProbeFailed){$flags+='D3D9EX_SHARED_PROBE_FAILED'}
if($driverSeatCount -gt 0){$flags+='DRIVER_SEAT_CAMERA_ACTIVE'}
if($directFrames -eq 0 -and $directFallbacks -gt 0){$flags+='DIRECT_GPU_NOT_ACTIVE'}
if($crashEvidence){$flags+='CRASH_TEXT_PRESENT'}
if($whiteScreenEvidence){$flags+='WHITE_SCREEN_TEXT_PRESENT'}
if($perfSpikeCount -gt 0){$flags+='DX9EX_FRAME_SPIKES_PRESENT'}
if($rankProjectionNotReached){$flags+='HUD_RANK_PROJECTED_PATH_ZERO'}
if($hudStereoEyeRejected){$flags+='HUD_STEREO_EYE_REJECTED'}
if($hudD3dxFlushFailed){$flags+='HUD_D3DX_FLUSH_FAILED'}
if($gameDllMismatch){$flags+='GAME_DLL_SHA256_MISMATCH'}
if($flags.Count -eq 0){$flags+='NO_AUTOMATIC_RED_FLAG'}

$variant=if($session.VariantId){[string]$session.VariantId}else{'UNKNOWN'}
$backend=if($session.Backend){[string]$session.Backend}else{'UNKNOWN'}
$profile=if($session.TestProfile){[string]$session.TestProfile}else{'UNKNOWN'}
$sourceSha=if($session.SourceSha){[string]$session.SourceSha}else{'UNKNOWN'}

$status='OK'
if($sbsFallback -and $backend -match 'dxvk'){$status='DXVK_SBS_FALLBACK_CONFIRMED'}
elseif($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){$status='UNEXPECTED_DRIVER_SEAT_CAMERA_ACTIVE'}
elseif($directFrames -eq 0 -and $directFallbacks -gt 0){$status='DIRECT_GPU_UNAVAILABLE'}
elseif($gameDllMismatch){$status='GAME_DLL_SHA256_MISMATCH'}
elseif($rankProjectionNotReached){$status='HUD_RANK_PROJECTED_PATH_ZERO'}
elseif($hudStereoEyeRejected){$status='HUD_STEREO_EYE_REJECTED'}
elseif($hudD3dxFlushFailed){$status='HUD_D3DX_FLUSH_FAILED'}

$result=[ordered]@{
    SchemaVersion=1
    Status=$status
    VariantId=$variant
    Backend=$backend
    TestProfile=$profile
    SourceSha=$sourceSha
    Provider=$provider
    SBSDesktopDupFallback=$sbsFallback
    PlainD3D9Device=$plainD3D9
    SharedD3D9ExProbeFailed=$sharedProbeFailed
    RankProducerObserved=$rankProducerObserved
    ProjectedMarkerSemanticCount=$projectedSemantic
    HudStereoEyeRejected=$hudStereoEyeRejected
    HudD3dxFlushFailed=$hudD3dxFlushFailed
    GameDllIdentityMismatch=$gameDllMismatch
    DirectFrames=$directFrames
    DirectFallbacks=$directFallbacks
    FenceTimeouts=$fenceTimeout
    DriverSeatCameraActivationCount=$driverSeatCount
    ApproxAverageXrFrameMs=$avgFrameMs
    ApproxAverageXrHz=$approxHz
    PerfSpikeCount=$perfSpikeCount
    PerfSpikeMaxFrameUs=$perfSpikeMaxFrameUs
    PerfSpikeMaxDraws=$perfSpikeMaxDraws
    PerfSpikeMaxPrimitives=$perfSpikeMaxPrimitives
    PerfSpikeMaxParticleLikeDraws=$perfSpikeMaxParticleLikeDraws
    PerfSpikeMaxParticleLikePrimitives=$perfSpikeMaxParticleLikePrimitives
    PerfSpikeMaxFenceWaitUs=$perfSpikeMaxFenceWaitUs
    Flags=$flags
}
$result|ConvertTo-Json -Depth 4|Set-Content (Join-Path $SessionDir 'AUTO_ANALYSIS_SUMMARY.json') -Encoding UTF8

$lines=@(
    'OUTRUN VR AUTO ANALYSIS'
    "status=$status"
    "variant=$variant"
    "backend=$backend"
    "profile=$profile"
    "sourceSha=$sourceSha"
    "provider=$provider"
    "sbsDesktopDupFallback=$sbsFallback"
    "plainD3D9Device=$plainD3D9"
    "sharedD3D9ExProbeFailed=$sharedProbeFailed"
    "rankProducerObserved=$rankProducerObserved"
    "projectedMarkerSemanticCount=$projectedSemantic"
    "hudStereoEyeRejected=$hudStereoEyeRejected"
    "hudD3dxFlushFailed=$hudD3dxFlushFailed"
    "gameDllIdentityMismatch=$gameDllMismatch"
    "directFrames=$directFrames"
    "directFallbacks=$directFallbacks"
    "fenceTimeouts=$fenceTimeout"
    "driverSeatCameraActivationCount=$driverSeatCount"
    ("approxAverageXrFrameMs="+$(if($null -ne $avgFrameMs){'{0:F3}' -f $avgFrameMs}else{'n/a'}))
    ("approxAverageXrHz="+$(if($null -ne $approxHz){'{0:F1}' -f $approxHz}else{'n/a'}))
    "perfSpikeCount=$perfSpikeCount"
    "perfSpikeMaxFrameUs=$perfSpikeMaxFrameUs"
    "perfSpikeMaxDraws=$perfSpikeMaxDraws"
    "perfSpikeMaxPrimitives=$perfSpikeMaxPrimitives"
    "perfSpikeMaxParticleLikeDraws=$perfSpikeMaxParticleLikeDraws"
    "perfSpikeMaxParticleLikePrimitives=$perfSpikeMaxParticleLikePrimitives"
    "perfSpikeMaxFenceWaitUs=$perfSpikeMaxFenceWaitUs"
    "flags=$($flags -join ',')"
)
if($status -eq 'DXVK_SBS_FALLBACK_CONFIRMED'){
    $lines+='interpretation=DXVK loaded, but DirectGPU shared-eye transport did not activate; runtime fell back to SBS/Desktop Duplication.'
}
if($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){
    $lines+='interpretation_camera=Driver-seat camera code activated during a non-cockpit test slot.'
}
$lines|Set-Content (Join-Path $SessionDir 'AUTO_ANALYSIS_SUMMARY.txt') -Encoding UTF8
Write-Host ($lines -join [Environment]::NewLine)
