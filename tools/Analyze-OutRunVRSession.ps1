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
# R32's current FRAME SPIKE producer ends the workload record with stereo[...]
# and does NOT emit fenceWaitUs/fencePolls. Requiring those optional legacy
# counters silently discarded EVERY current source-side spike sample.
# Match one log line only and parse legacy fence counters separately.
$perfSpikePattern='VR R32 FRAME SPIKE: frameUs=(\d+) baselineUs=(\d+) presentUs=(\d+).*?draws=(\d+),primitives=(\d+),triangles=(\d+),indexed=(\d+),up=(\d+),alphaBlend=(\d+),alphaBlendPrimitives=(\d+),alphaTest=(\d+),particleLikeDraws=(\d+),particleLikePrimitives=(\d+),effectUnknown=(\d+)[^\r\n]*'
foreach($spike in [regex]::Matches($gameLog,$perfSpikePattern)){
    $fenceMatch=[regex]::Match($spike.Value,'fenceWaitUs=(\d+),fencePolls=(\d+)')
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
        FenceWaitUs=$(if($fenceMatch.Success){[int64]$fenceMatch.Groups[1].Value}else{$null})
        FencePolls=$(if($fenceMatch.Success){[int64]$fenceMatch.Groups[2].Value}else{$null})
    }
}
# The active R28 lower-Present path emits the guaranteed source-frame
# fallback diagnostics for CORRECTNESS. Count its throttled events separately
# from detailed R32 GPU/effect counters; absent optional fields remain zero.
$r28DipPattern='VR R28 FRAME DIP: frameMs=([0-9.]+) presentMs=([0-9.]+) estimateFps=([0-9.]+) draws=(\d+) frameSerial=(\d+)(?: band=(BELOW(?:60|50|40|30)))?[^\r\n]*'
$r28DipRows=@()
foreach($dip in [regex]::Matches($gameLog,$r28DipPattern)){
    $r28DipRows += [pscustomobject]@{
        FrameMs=[double]::Parse($dip.Groups[1].Value,[Globalization.CultureInfo]::InvariantCulture)
        PresentMs=[double]::Parse($dip.Groups[2].Value,[Globalization.CultureInfo]::InvariantCulture)
        Draws=[int64]$dip.Groups[4].Value
        FrameSerial=[int64]$dip.Groups[5].Value
        Band=$(if($dip.Groups[6].Success){$dip.Groups[6].Value}else{'LEGACY_UNKNOWN'})
        PrepMs=$(if($dip.Value -match 'prepMs=([0-9.]+)'){[double]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)}else{$null})
        ThreadCpuMs=$(if($dip.Value -match 'threadCpuMs=([0-9.]+)'){[double]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)}else{$null})
        NonCpuMs=$(if($dip.Value -match 'nonCpuMs=([0-9.]+)'){[double]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)}else{$null})
        CpuKnown=$(if($dip.Value -match 'cpuKnown=([01])'){[int]$Matches[1]}else{$null})
    }
}
if($r28DipRows.Count -gt 0){
    $r28DipRows|Export-Csv (Join-Path $SessionDir 'R28_ACTIVE_FRAME_DIPS.csv') -NoTypeInformation -Encoding UTF8
}
$r28PacingRows=@([regex]::Matches($gameLog,
    'VR R28 FRAME WINDOW 5s: frames=(\d+) sampled=(\d+) avgMs=([0-9.]+) p95Ms=([0-9.]+) p99Ms=([0-9.]+) maxMs=([0-9.]+) presentMaxMs=([0-9.]+) over16ms=(\d+)(?: over20ms=(\d+))? over25ms=(\d+) over33ms=(\d+) drawPeak=(\d+) drawPeakAtDip=(\d+)'))
$r28Below60=0
$r28Below50=0
$r28Over25=0
$r28Over33=0
$r28MaxSourceMs=0.0
foreach($w in $r28PacingRows){
    $r28Below60 += [int64]$w.Groups[8].Value
    if($w.Groups[9].Success){$r28Below50 += [int64]$w.Groups[9].Value}
    $r28Over25 += [int64]$w.Groups[10].Value
    $r28Over33 += [int64]$w.Groups[11].Value
    $r28MaxSourceMs = [math]::Max($r28MaxSourceMs,
        [double]::Parse($w.Groups[6].Value,[Globalization.CultureInfo]::InvariantCulture))
}
# Paired, 5-second render-thread CPU/wall-time diagnostics from R28.
# This summary does not claim to measure GPU occupancy or precise fence waits.
$r28CpuPattern='VR R28 CPU WINDOW 5s: frames=(\d+) cpuSamples=(\d+) avgPrepMs=([0-9.]+) maxPrepMs=([0-9.]+) avgThreadCpuMs=([0-9.]+) maxThreadCpuMs=([0-9.]+) avgNonCpuMs=([0-9.]+) maxNonCpuMs=([0-9.]+) slowCpuDominant=(\d+) slowNonCpuDominant=(\d+) slowMixed=(\d+) slowNoCpuSample=(\d+)'
$r28CpuRows=@()
foreach($cpu in [regex]::Matches($gameLog,$r28CpuPattern)){
    $r28CpuRows += [pscustomobject]@{
        Frames=[int64]$cpu.Groups[1].Value
        CpuSamples=[int64]$cpu.Groups[2].Value
        AvgPrepMs=[double]::Parse($cpu.Groups[3].Value,[Globalization.CultureInfo]::InvariantCulture)
        MaxPrepMs=[double]::Parse($cpu.Groups[4].Value,[Globalization.CultureInfo]::InvariantCulture)
        AvgThreadCpuMs=[double]::Parse($cpu.Groups[5].Value,[Globalization.CultureInfo]::InvariantCulture)
        MaxThreadCpuMs=[double]::Parse($cpu.Groups[6].Value,[Globalization.CultureInfo]::InvariantCulture)
        AvgNonCpuMs=[double]::Parse($cpu.Groups[7].Value,[Globalization.CultureInfo]::InvariantCulture)
        MaxNonCpuMs=[double]::Parse($cpu.Groups[8].Value,[Globalization.CultureInfo]::InvariantCulture)
        SlowCpuDominant=[int64]$cpu.Groups[9].Value
        SlowNonCpuDominant=[int64]$cpu.Groups[10].Value
        SlowMixed=[int64]$cpu.Groups[11].Value
        SlowNoCpuSample=[int64]$cpu.Groups[12].Value
    }
}
$r28SlowCpuDominant=0
$r28SlowNonCpuDominant=0
$r28SlowMixed=0
$r28SlowNoCpuSample=0
$r28MaxPrepMs=0.0
$r28MaxThreadCpuMs=0.0
$r28MaxNonCpuMs=0.0
foreach($cpu in $r28CpuRows){
    $r28SlowCpuDominant += $cpu.SlowCpuDominant
    $r28SlowNonCpuDominant += $cpu.SlowNonCpuDominant
    $r28SlowMixed += $cpu.SlowMixed
    $r28SlowNoCpuSample += $cpu.SlowNoCpuSample
    $r28MaxPrepMs=[math]::Max($r28MaxPrepMs,$cpu.MaxPrepMs)
    $r28MaxThreadCpuMs=[math]::Max($r28MaxThreadCpuMs,$cpu.MaxThreadCpuMs)
    $r28MaxNonCpuMs=[math]::Max($r28MaxNonCpuMs,$cpu.MaxNonCpuMs)
}
if($r28CpuRows.Count -gt 0){
    $r28CpuRows|Export-Csv (Join-Path $SessionDir 'R28_CPU_BREAKDOWN_5S.csv') -NoTypeInformation -Encoding UTF8
}
$perfSpikeCount=$perfSpikeRows.Count + $r28DipRows.Count
$perfSpikeMaxFrameUs=0
$perfSpikeMaxDraws=0
$perfSpikeMaxPrimitives=0
$perfSpikeMaxParticleLikeDraws=0
$perfSpikeMaxParticleLikePrimitives=0
$perfSpikeMaxFenceWaitUs=0
$perfSpikeFenceTelemetryAvailable=$false
if($perfSpikeRows.Count -gt 0){
    $perfSpikeMaxFrameUs=($perfSpikeRows|Measure-Object FrameUs -Maximum).Maximum
    $perfSpikeMaxDraws=($perfSpikeRows|Measure-Object Draws -Maximum).Maximum
    $perfSpikeMaxPrimitives=($perfSpikeRows|Measure-Object Primitives -Maximum).Maximum
    $perfSpikeMaxParticleLikeDraws=($perfSpikeRows|Measure-Object ParticleLikeDraws -Maximum).Maximum
    $perfSpikeMaxParticleLikePrimitives=($perfSpikeRows|Measure-Object ParticleLikePrimitives -Maximum).Maximum
    $measuredFenceRows=@($perfSpikeRows|Where-Object{$null -ne $_.FenceWaitUs})
    if($measuredFenceRows.Count -gt 0){
        $perfSpikeFenceTelemetryAvailable=$true
        $perfSpikeMaxFenceWaitUs=($measuredFenceRows|Measure-Object FenceWaitUs -Maximum).Maximum
    }
    $perfSpikeRows|Export-Csv (Join-Path $SessionDir 'PERFORMANCE_SPIKES.csv') -NoTypeInformation -Encoding UTF8
}

# R32 spike samples are optional and do not cover all D3D9Ex lower-Present
# stalls. The 2026-10-09 HMD log reported 28.557 ms lower-Present yet emitted
# zero R32 FRAME SPIKE rows. Compare R28's observed per-window max against
# the headset's reported refresh budget; do not mistake zero R32 samples for
# zero real render stalls.
if($r28DipRows.Count -gt 0){
    $perfSpikeMaxFrameUs=[math]::Max([int64]$perfSpikeMaxFrameUs,
        [int64](1000 * ($r28DipRows|Measure-Object FrameMs -Maximum).Maximum))
    $perfSpikeMaxDraws=[math]::Max([int64]$perfSpikeMaxDraws,
        [int64]($r28DipRows|Measure-Object Draws -Maximum).Maximum)
}

$presentLatencyRows=@()
$xrBudgetMs=16.6667
$reportedXrHz=0.0
$reportedHzMatch=Get-LastRegexMatch $hostLog 'actualXrHz=([0-9]+(?:\.[0-9]+)?)'
if($reportedHzMatch){
    [double]::TryParse($reportedHzMatch.Groups[1].Value,
        [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture,
        [ref]$reportedXrHz)|Out-Null
}
if($reportedXrHz -ge 60.0 -and $reportedXrHz -le 144.0){
    $xrBudgetMs=1000.0/$reportedXrHz
}
foreach($present in [regex]::Matches($gameLog,
    'VR R28 PERF: lower-Present avgMs=([0-9.]+) maxMs=([0-9.]+) drawsPerPresent=([0-9.]+)')){
    $maxMs=0.0
    if([double]::TryParse($present.Groups[2].Value,
        [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture,
        [ref]$maxMs) -and $maxMs -gt 0){
        $presentLatencyRows+= $maxMs
    }
}
$presentLatencyMaxMs=0.0
$presentOverBudgetWindows=0
if($presentLatencyRows.Count -gt 0){
    $presentLatencyMaxMs=($presentLatencyRows|Measure-Object -Maximum).Maximum
    $presentOverBudgetWindows=@($presentLatencyRows|Where-Object{$_ -gt $xrBudgetMs}).Count
}
$gameDefaultWidth=0
$gameDefaultHeight=0
$resolutionMatch=Get-LastRegexMatch $gameLog 'GameDefaultConfigOverride: default resolution set to (\d+)x(\d+)'
if($resolutionMatch){
    $gameDefaultWidth=[int]$resolutionMatch.Groups[1].Value
    $gameDefaultHeight=[int]$resolutionMatch.Groups[2].Value
}

# A result/GOAL transition can render unowned queue overlays first and
# exact TEXT_GLYPH ScreenHud later while both are STATE_GOAL. An overall
# log status=OK does not prove that map/time animation and the completed
# result share the same per-eye transform. This is *mixed ownership evidence*,
# NOT a diagnosis that the generic draw is necessarily the offending text.
$goalGenericPhaseEvidence=($gameLog -match 'VR P0 GOAL EARLY_GATE:.*?producer=NONE scope=SCREEN_OVERLAY_2D')
$goalExactTextEvidence=($gameLog -match 'VR P0 GOAL EARLY_GATE:.*?producer=TEXT_GLYPH_PUTSPRITE scope=SCREEN_HUD')
$goalMixedPhaseOwnerEvidence=($goalGenericPhaseEvidence -and $goalExactTextEvidence)
# The original lens producer hook applies to an entire effect CALL. Logs
# cannot tell which of the 4-5 discs is the offending central core.
$lensProducerHookObserved=($gameLog -match 'VR P0 FLARE: exact EXE\+0xCABE producer')

# The original rank CALLs can run without any actual R57 projected draw.
# A no-red-flag verdict is false in that case; report the missing ownership.
$rankTrace=Read-AllText 'HUD_TRACE_SUMMARY.txt'
$rankProducerObserved=($rankTrace -match 'RankMarker/sub_4BAD20')
$projectedSemantic=-1
$projectedSummary=Get-LastRegexMatch $gameLog 'projected\[semantic=(\d+),missingPayload='
if($projectedSummary){$projectedSemantic=[int64]$projectedSummary.Groups[1].Value}
$rankProjectionNotReached=($rankProducerObserved -and $projectedSemantic -eq 0)
# Projected counters aggregate rank AND the already-working OutRun rival.
# A healthy rival must not mask absence of the rank-only Calc3D2D callback.
$rankExactCalcObserved=($gameLog -match 'VR R57 rank Calc3D2D: ordinal capture')
$rankExactCalcUnobserved=($rankProducerObserved -and $projectedSemantic -gt 0 -and -not $rankExactCalcObserved)

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
if($presentOverBudgetWindows -gt 0){$flags+='D3D9EX_PRESENT_LATENCY_OVER_XR_BUDGET'}
if($rankProjectionNotReached){$flags+='HUD_RANK_PROJECTED_PATH_ZERO'}
if($rankExactCalcUnobserved){$flags+='HUD_RANK_CALC_CAPTURE_UNOBSERVED'}
if($goalMixedPhaseOwnerEvidence){$flags+='GOAL_MIXED_GENERIC_VS_EXACT_HUD_NEEDS_PHASE_REVIEW'}
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
elseif($rankExactCalcUnobserved){$status='HUD_RANK_CALC_CAPTURE_UNOBSERVED'}
elseif($presentOverBudgetWindows -gt 0 -or $perfSpikeCount -gt 0){$status='PERFORMANCE_WARNING'}
elseif($goalMixedPhaseOwnerEvidence){$status='NEEDS_GOAL_PHASE_VISUAL_REVIEW'}

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
    RankExactCalcObserved=$rankExactCalcObserved
    GameDllIdentityMismatch=$gameDllMismatch
    GoalGenericPhaseEvidence=$goalGenericPhaseEvidence
    GoalExactTextEvidence=$goalExactTextEvidence
    GoalMixedPhaseOwnerEvidence=$goalMixedPhaseOwnerEvidence
    LensProducerHookObserved=$lensProducerHookObserved
    LensCenterOpticalStatus='NOT_INFERABLE_FROM_LOGS'
    ResultProgressOpticalStatus='NOT_INFERABLE_FROM_LOGS'
    DirectFrames=$directFrames
    DirectFallbacks=$directFallbacks
    FenceTimeouts=$fenceTimeout
    DriverSeatCameraActivationCount=$driverSeatCount
    ApproxAverageXrFrameMs=$avgFrameMs
    ApproxAverageXrHz=$approxHz
    GameDefaultWidth=$gameDefaultWidth
    GameDefaultHeight=$gameDefaultHeight
    XrRefreshBudgetMs=$xrBudgetMs
    R28PresentSampleWindows=$presentLatencyRows.Count
    R28PresentOverBudgetWindows=$presentOverBudgetWindows
    R28PresentMaxMs=$presentLatencyMaxMs
    R28ActivePacingWindows=$r28PacingRows.Count
    R28ActiveBelow60FpsFrames=$r28Below60
    R28ActiveBelow50FpsFrames=$r28Below50
    R28ActiveOver25ms=$r28Over25
    R28ActiveOver33ms=$r28Over33
    R28ActiveMaxSourceFrameMs=$r28MaxSourceMs
    R28CpuDiagnosticWindows=$r28CpuRows.Count
    R28SlowCpuDominantFrames=$r28SlowCpuDominant
    R28SlowNonCpuDominantFrames=$r28SlowNonCpuDominant
    R28SlowMixedFrames=$r28SlowMixed
    R28SlowNoCpuSampleFrames=$r28SlowNoCpuSample
    R28MaxPrepMs=$r28MaxPrepMs
    R28MaxThreadCpuMs=$r28MaxThreadCpuMs
    R28MaxNonCpuMs=$r28MaxNonCpuMs
    PerfSpikeCount=$perfSpikeCount
    PerfSpikeMaxFrameUs=$perfSpikeMaxFrameUs
    PerfSpikeMaxDraws=$perfSpikeMaxDraws
    PerfSpikeMaxPrimitives=$perfSpikeMaxPrimitives
    PerfSpikeMaxParticleLikeDraws=$perfSpikeMaxParticleLikeDraws
    PerfSpikeMaxParticleLikePrimitives=$perfSpikeMaxParticleLikePrimitives
    PerfSpikeMaxFenceWaitUs=$perfSpikeMaxFenceWaitUs
    PerfSpikeFenceTelemetryAvailable=$perfSpikeFenceTelemetryAvailable
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
    "rankExactCalcObserved=$rankExactCalcObserved"
    "gameDllIdentityMismatch=$gameDllMismatch"
    "goalMixedPhaseOwnerEvidence=$goalMixedPhaseOwnerEvidence"
    "lensProducerHookObserved=$lensProducerHookObserved"
    "lensCenterOpticalStatus=NOT_INFERABLE_FROM_LOGS"
    "resultProgressOpticalStatus=NOT_INFERABLE_FROM_LOGS"
    "directFrames=$directFrames"
    "directFallbacks=$directFallbacks"
    "fenceTimeouts=$fenceTimeout"
    "driverSeatCameraActivationCount=$driverSeatCount"
    ("approxAverageXrFrameMs="+$(if($null -ne $avgFrameMs){'{0:F3}' -f $avgFrameMs}else{'n/a'}))
    ("approxAverageXrHz="+$(if($null -ne $approxHz){'{0:F1}' -f $approxHz}else{'n/a'}))
    "gameDefaultResolution=${gameDefaultWidth}x${gameDefaultHeight}"
    ("xrRefreshBudgetMs="+('{0:F3}' -f $xrBudgetMs))
    "r28PresentSampleWindows=$($presentLatencyRows.Count)"
    "r28PresentOverBudgetWindows=$presentOverBudgetWindows"
    ("r28PresentMaxMs="+('{0:F3}' -f $presentLatencyMaxMs))
    "r28ActivePacingWindows=$($r28PacingRows.Count)"
    "r28ActiveBelow60FpsFrames=$r28Below60"
    "r28ActiveBelow50FpsFrames=$r28Below50"
    "r28ActiveOver25ms=$r28Over25"
    "r28ActiveOver33ms=$r28Over33"
    ("r28ActiveMaxSourceFrameMs="+('{0:F3}' -f $r28MaxSourceMs))
    "r28CpuDiagnosticWindows=$($r28CpuRows.Count)"
    "r28SlowCpuDominantFrames=$r28SlowCpuDominant"
    "r28SlowNonCpuDominantFrames=$r28SlowNonCpuDominant"
    "r28SlowMixedFrames=$r28SlowMixed"
    "r28SlowNoCpuSampleFrames=$r28SlowNoCpuSample"
    ("r28MaxPrepMs="+('{0:F3}' -f $r28MaxPrepMs))
    ("r28MaxThreadCpuMs="+('{0:F3}' -f $r28MaxThreadCpuMs))
    ("r28MaxNonCpuMs="+('{0:F3}' -f $r28MaxNonCpuMs))
    "perfSpikeCount=$perfSpikeCount"
    "perfSpikeMaxFrameUs=$perfSpikeMaxFrameUs"
    "perfSpikeMaxDraws=$perfSpikeMaxDraws"
    "perfSpikeMaxPrimitives=$perfSpikeMaxPrimitives"
    "perfSpikeMaxParticleLikeDraws=$perfSpikeMaxParticleLikeDraws"
    "perfSpikeMaxParticleLikePrimitives=$perfSpikeMaxParticleLikePrimitives"
    "perfSpikeMaxFenceWaitUs=$perfSpikeMaxFenceWaitUs"
    "perfSpikeFenceTelemetryAvailable=$perfSpikeFenceTelemetryAvailable"
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
