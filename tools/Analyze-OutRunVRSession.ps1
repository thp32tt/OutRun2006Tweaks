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

$semanticRegistered=0
$semanticConsumed=0
$semanticStaleCleared=0
$semantic=Get-LastRegexMatch $gameLog 'VR HUD SEMANTIC R53: queuePass=\d+ registered=(\d+) consumed=(\d+) staleCleared=(\d+)'
if($semantic){
    $semanticRegistered=[int64]$semantic.Groups[1].Value
    $semanticConsumed=[int64]$semantic.Groups[2].Value
    $semanticStaleCleared=[int64]$semantic.Groups[3].Value
}

$recenterPublished=([regex]::Matches($gameLog,'VR recenter: published host requestId=')).Count
$recenterGameplayApplied=([regex]::Matches($gameLog,'VR renderer: yaw recentered gameplay pose')).Count
$recenterHostReceived=([regex]::Matches($hostLog,'(?i)recenter.*(?:received.*requestId|requestId=.*received)|requestId=.*recenter.*received')).Count
$recenterHostApplied=([regex]::Matches($hostLog,'(?i)recenter.*requestId=.*applied|requestId=.*completed by fresh visible|anchorUpdated=1 submitSuccess=1')).Count

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

$flags=@()
if($sbsFallback){$flags+='SBS_DESKTOP_DUP_FALLBACK'}
if($plainD3D9){$flags+='PLAIN_D3D9_PROVIDER'}
if($sharedProbeFailed){$flags+='D3D9EX_SHARED_PROBE_FAILED'}
if($driverSeatCount -gt 0){$flags+='DRIVER_SEAT_CAMERA_ACTIVE'}
if($directFrames -eq 0 -and $directFallbacks -gt 0){$flags+='DIRECT_GPU_NOT_ACTIVE'}
if($crashEvidence){$flags+='CRASH_TEXT_PRESENT'}
if($whiteScreenEvidence){$flags+='WHITE_SCREEN_TEXT_PRESENT'}
if($flags.Count -eq 0){$flags+='NO_AUTOMATIC_RED_FLAG'}

$variant=if($session.VariantId){[string]$session.VariantId}else{'UNKNOWN'}
$backend=if($session.Backend){[string]$session.Backend}else{'UNKNOWN'}
$profile=if($session.TestProfile){[string]$session.TestProfile}else{'UNKNOWN'}
$sourceSha=if($session.SourceSha){[string]$session.SourceSha}else{'UNKNOWN'}

$status='OK'
if($sbsFallback -and $backend -match 'dxvk'){$status='DXVK_SBS_FALLBACK_CONFIRMED'}
elseif($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){$status='UNEXPECTED_DRIVER_SEAT_CAMERA_ACTIVE'}
elseif($directFrames -eq 0 -and $directFallbacks -gt 0){$status='DIRECT_GPU_UNAVAILABLE'}

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
    DirectFrames=$directFrames
    DirectFallbacks=$directFallbacks
    FenceTimeouts=$fenceTimeout
    DriverSeatCameraActivationCount=$driverSeatCount
    SemanticRegistered=$semanticRegistered
    SemanticConsumed=$semanticConsumed
    SemanticStaleCleared=$semanticStaleCleared
    RecenterPublished=$recenterPublished
    RecenterGameplayApplied=$recenterGameplayApplied
    RecenterHostReceived=$recenterHostReceived
    RecenterHostApplied=$recenterHostApplied
    ApproxAverageXrFrameMs=$avgFrameMs
    ApproxAverageXrHz=$approxHz
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
    "directFrames=$directFrames"
    "directFallbacks=$directFallbacks"
    "fenceTimeouts=$fenceTimeout"
    "driverSeatCameraActivationCount=$driverSeatCount"
    "semanticRegistered=$semanticRegistered"
    "semanticConsumed=$semanticConsumed"
    "semanticStaleCleared=$semanticStaleCleared"
    "recenterPublished=$recenterPublished"
    "recenterGameplayApplied=$recenterGameplayApplied"
    "recenterHostReceived=$recenterHostReceived"
    "recenterHostApplied=$recenterHostApplied"
    ("approxAverageXrFrameMs="+$(if($null -ne $avgFrameMs){'{0:F3}' -f $avgFrameMs}else{'n/a'}))
    ("approxAverageXrHz="+$(if($null -ne $approxHz){'{0:F1}' -f $approxHz}else{'n/a'}))
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
