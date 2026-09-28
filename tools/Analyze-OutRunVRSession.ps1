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

function Read-OptionalJson([string]$name){
    $path=Join-Path $SessionDir $name
    if(!(Test-Path $path -PathType Leaf)){return $null}
    try{return Get-Content $path -Raw|ConvertFrom-Json}catch{return $null}
}

$session=@{}
$manifestPath=Join-Path $SessionDir 'session_manifest.json'
if(Test-Path $manifestPath){
    try{$session=Get-Content $manifestPath -Raw|ConvertFrom-Json}catch{$session=@{}}
}
$buildInputs=Read-OptionalJson 'BUILD_INPUTS.json'
$oneClickPreflight=Read-OptionalJson 'VR_ONE_CLICK_PREFLIGHT.json'

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
$sharedProbeFailurePatterns=[ordered]@{
    LEGACY_VERIFY='shared verification texture creation/upload failed'
    DXVK_OPEN_D3DKMT='Failed to open shared D3DKMT handle'
    DXVK_WRITE_SHARED_INFO='Failed to write shared resource info for a texture'
}
$sharedProbeFailureReasons=@()
foreach($entry in $sharedProbeFailurePatterns.GetEnumerator()){
    if($combined -match [regex]::Escape([string]$entry.Value)){
        $sharedProbeFailureReasons+=[string]$entry.Key
    }
}
$sharedProbeFailed=($sharedProbeFailureReasons.Count -gt 0)

$dxvkHostBridgeReadyMatch=Get-LastRegexMatch $hostLog 'DXVK host-owned shared-eye bridge ready:\s*(\d+)x(\d+)\s*x2,\s*slots=(\d+),\s*generation=(\d+)'
$dxvkHostBridgeAllocationFailed=($hostLog -match 'DXVK host-owned shared-eye bridge allocation failed')
$dxvkHostImportReadyMatch=Get-LastRegexMatch $gameLog 'VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring\s+(\d+)x(\d+)\s+generation=(\d+)'
$dxvkHostImportFailed=($gameLog -match 'VR DXVK native transport: host-owned KMT eye import failed')
$dxvkHostPathActive=($gameLog -match 'path=DXVK host-owned D3D11 KMT import')
$dxvkHostBridgeReady=($null -ne $dxvkHostBridgeReadyMatch)
$dxvkHostImportReady=($null -ne $dxvkHostImportReadyMatch)
$dxvkHostBridgeWidth=if($dxvkHostBridgeReady){[int]$dxvkHostBridgeReadyMatch.Groups[1].Value}else{0}
$dxvkHostBridgeHeight=if($dxvkHostBridgeReady){[int]$dxvkHostBridgeReadyMatch.Groups[2].Value}else{0}
$dxvkHostBridgeSlots=if($dxvkHostBridgeReady){[int]$dxvkHostBridgeReadyMatch.Groups[3].Value}else{0}
$dxvkHostBridgeGeneration=if($dxvkHostBridgeReady){[uint32]$dxvkHostBridgeReadyMatch.Groups[4].Value}else{0}
$dxvkHostImportWidth=if($dxvkHostImportReady){[int]$dxvkHostImportReadyMatch.Groups[1].Value}else{0}
$dxvkHostImportHeight=if($dxvkHostImportReady){[int]$dxvkHostImportReadyMatch.Groups[2].Value}else{0}
$dxvkHostImportGeneration=if($dxvkHostImportReady){[uint32]$dxvkHostImportReadyMatch.Groups[3].Value}else{0}
$dxvkHostGenerationMatches=if($dxvkHostBridgeReady -and $dxvkHostImportReady){$dxvkHostBridgeGeneration -eq $dxvkHostImportGeneration}else{$null}
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
if($dxvkHostBridgeAllocationFailed){$flags+='DXVK_HOST_BRIDGE_ALLOCATION_FAILED'}
if($dxvkHostBridgeReady){$flags+='DXVK_HOST_BRIDGE_READY'}
if($dxvkHostImportFailed){$flags+='DXVK_HOST_BRIDGE_IMPORT_FAILED'}
if($dxvkHostImportReady){$flags+='DXVK_HOST_BRIDGE_IMPORT_READY'}
if($dxvkHostPathActive){$flags+='DXVK_HOST_DIRECT_PATH_ACTIVE'}
if($backend -match 'dxvk' -and $buildIdentityMismatch){$flags+='DXVK_BUILD_IDENTITY_MISMATCH'}
elseif($backend -match 'dxvk' -and -not $buildIdentityComplete){$flags+='DXVK_BUILD_IDENTITY_INCOMPLETE'}
elseif($backend -match 'dxvk' -and $buildIdentityVerified){$flags+='DXVK_BUILD_IDENTITY_VERIFIED'}
if($driverSeatCount -gt 0){$flags+='DRIVER_SEAT_CAMERA_ACTIVE'}
if($directFrames -eq 0 -and $directFallbacks -gt 0){$flags+='DIRECT_GPU_NOT_ACTIVE'}
if($crashEvidence){$flags+='CRASH_TEXT_PRESENT'}
if($whiteScreenEvidence){$flags+='WHITE_SCREEN_TEXT_PRESENT'}
if($flags.Count -eq 0){$flags+='NO_AUTOMATIC_RED_FLAG'}

$variant=if($session.VariantId){[string]$session.VariantId}else{'UNKNOWN'}
$backend=if($session.Backend){[string]$session.Backend}else{'UNKNOWN'}
$profile=if($session.TestProfile){[string]$session.TestProfile}else{'UNKNOWN'}
$sourceSha=if($session.SourceSha){[string]$session.SourceSha}else{'UNKNOWN'}

$buildIdentityIssues=@()
$buildInputSourceSha=''
$preflightSourceSha=''
$preflightBackend=''
$buildInputBackend=''
$buildIdentityEvidenceCount=0
if($null -ne $buildInputs){
    if($buildInputs.IntegrationSha){$buildInputSourceSha=[string]$buildInputs.IntegrationSha;$buildIdentityEvidenceCount++}
    if($buildInputs.LaunchBackend){$buildInputBackend=[string]$buildInputs.LaunchBackend}
}
if($null -ne $oneClickPreflight){
    if($oneClickPreflight.SourceSha){$preflightSourceSha=[string]$oneClickPreflight.SourceSha;$buildIdentityEvidenceCount++}
    if($oneClickPreflight.ResolvedBackend){$preflightBackend=[string]$oneClickPreflight.ResolvedBackend}
    if($oneClickPreflight.PackageBuildInputs -and $oneClickPreflight.PackageBuildInputs.IntegrationSha){
        $preflightInputSha=[string]$oneClickPreflight.PackageBuildInputs.IntegrationSha
        if($preflightSourceSha -and $preflightInputSha -ne $preflightSourceSha){$buildIdentityIssues+='PREFLIGHT_PACKAGE_SOURCE_MISMATCH'}
    }
}
if($sourceSha -and $sourceSha -ne 'UNKNOWN'){
    if($buildInputSourceSha -and $buildInputSourceSha -ne $sourceSha){$buildIdentityIssues+='SESSION_BUILD_INPUT_SOURCE_MISMATCH'}
    if($preflightSourceSha -and $preflightSourceSha -ne $sourceSha){$buildIdentityIssues+='SESSION_PREFLIGHT_SOURCE_MISMATCH'}
}
if($buildInputSourceSha -and $preflightSourceSha -and $buildInputSourceSha -ne $preflightSourceSha){$buildIdentityIssues+='BUILD_INPUT_PREFLIGHT_SOURCE_MISMATCH'}
if($backend -and $backend -ne 'UNKNOWN'){
    if($buildInputBackend -and $buildInputBackend -ne $backend){$buildIdentityIssues+='SESSION_BUILD_INPUT_BACKEND_MISMATCH'}
    if($preflightBackend -and $preflightBackend -ne $backend){$buildIdentityIssues+='SESSION_PREFLIGHT_BACKEND_MISMATCH'}
}
if($buildInputBackend -and $preflightBackend -and $buildInputBackend -ne $preflightBackend){$buildIdentityIssues+='BUILD_INPUT_PREFLIGHT_BACKEND_MISMATCH'}
$buildIdentityMismatch=($buildIdentityIssues.Count -gt 0)
$buildIdentityComplete=($sourceSha -ne 'UNKNOWN' -and $buildInputSourceSha -and $preflightSourceSha -and $buildInputBackend -and $preflightBackend)
$buildIdentityVerified=($buildIdentityComplete -and -not $buildIdentityMismatch)

$status='OK'
if($backend -match 'dxvk' -and $buildIdentityMismatch){$status='DXVK_BUILD_IDENTITY_MISMATCH'}
elseif($backend -match 'dxvk' -and $dxvkHostPathActive -and $directFrames -gt 0){$status='DXVK_HOST_OWNED_DIRECTGPU_ACTIVE'}
elseif($backend -match 'dxvk' -and $dxvkHostImportFailed){$status='DXVK_HOST_OWNED_IMPORT_FAILED'}
elseif($backend -match 'dxvk' -and $dxvkHostBridgeAllocationFailed){$status='DXVK_HOST_OWNED_BRIDGE_ALLOCATION_FAILED'}
elseif($backend -match 'dxvk' -and $dxvkHostBridgeReady -and -not $dxvkHostImportReady -and $directFrames -eq 0 -and $directFallbacks -gt 0){$status='DXVK_HOST_OWNED_IMPORT_NOT_ESTABLISHED'}
elseif($sbsFallback -and $backend -match 'dxvk'){$status='DXVK_SBS_FALLBACK_CONFIRMED'}
elseif($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){$status='UNEXPECTED_DRIVER_SEAT_CAMERA_ACTIVE'}
elseif($directFrames -eq 0 -and $directFallbacks -gt 0){$status='DIRECT_GPU_UNAVAILABLE'}

$result=[ordered]@{
    SchemaVersion=1
    Status=$status
    VariantId=$variant
    Backend=$backend
    TestProfile=$profile
    SourceSha=$sourceSha
    BuildIdentityComplete=$buildIdentityComplete
    BuildIdentityVerified=$buildIdentityVerified
    BuildIdentityMismatch=$buildIdentityMismatch
    BuildIdentityIssues=@($buildIdentityIssues)
    BuildInputSourceSha=$buildInputSourceSha
    PreflightSourceSha=$preflightSourceSha
    BuildInputBackend=$buildInputBackend
    PreflightBackend=$preflightBackend
    Provider=$provider
    SBSDesktopDupFallback=$sbsFallback
    PlainD3D9Device=$plainD3D9
    SharedD3D9ExProbeFailed=$sharedProbeFailed
    SharedD3D9ExProbeFailureReasons=@($sharedProbeFailureReasons)
    DxvkHostBridgeReady=$dxvkHostBridgeReady
    DxvkHostBridgeAllocationFailed=$dxvkHostBridgeAllocationFailed
    DxvkHostBridgeWidth=$dxvkHostBridgeWidth
    DxvkHostBridgeHeight=$dxvkHostBridgeHeight
    DxvkHostBridgeSlots=$dxvkHostBridgeSlots
    DxvkHostBridgeGeneration=$dxvkHostBridgeGeneration
    DxvkHostImportReady=$dxvkHostImportReady
    DxvkHostImportFailed=$dxvkHostImportFailed
    DxvkHostImportWidth=$dxvkHostImportWidth
    DxvkHostImportHeight=$dxvkHostImportHeight
    DxvkHostImportGeneration=$dxvkHostImportGeneration
    DxvkHostGenerationMatches=$dxvkHostGenerationMatches
    DxvkHostDirectPathActive=$dxvkHostPathActive
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
    "buildIdentityComplete=$buildIdentityComplete"
    "buildIdentityVerified=$buildIdentityVerified"
    "buildIdentityMismatch=$buildIdentityMismatch"
    "buildIdentityIssues=$($buildIdentityIssues -join ',')"
    "buildInputSourceSha=$buildInputSourceSha"
    "preflightSourceSha=$preflightSourceSha"
    "buildInputBackend=$buildInputBackend"
    "preflightBackend=$preflightBackend"
    "provider=$provider"
    "sbsDesktopDupFallback=$sbsFallback"
    "plainD3D9Device=$plainD3D9"
    "sharedD3D9ExProbeFailed=$sharedProbeFailed"
    "sharedD3D9ExProbeFailureReasons=$($sharedProbeFailureReasons -join ',')"
    "dxvkHostBridgeReady=$dxvkHostBridgeReady"
    "dxvkHostBridgeAllocationFailed=$dxvkHostBridgeAllocationFailed"
    "dxvkHostBridgeSize=$($dxvkHostBridgeWidth)x$($dxvkHostBridgeHeight)"
    "dxvkHostBridgeSlots=$dxvkHostBridgeSlots"
    "dxvkHostBridgeGeneration=$dxvkHostBridgeGeneration"
    "dxvkHostImportReady=$dxvkHostImportReady"
    "dxvkHostImportFailed=$dxvkHostImportFailed"
    "dxvkHostImportSize=$($dxvkHostImportWidth)x$($dxvkHostImportHeight)"
    "dxvkHostImportGeneration=$dxvkHostImportGeneration"
    "dxvkHostGenerationMatches=$dxvkHostGenerationMatches"
    "dxvkHostDirectPathActive=$dxvkHostPathActive"
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
if($status -eq 'DXVK_BUILD_IDENTITY_MISMATCH'){
    $lines+='interpretation=DXVK runtime evidence identity is inconsistent across session/build/preflight metadata; do not attribute DirectGPU or pacing results to a source SHA until the package/session mismatch is resolved.'
}
elseif($status -eq 'DXVK_HOST_OWNED_DIRECTGPU_ACTIVE'){
    $lines+='interpretation=DXVK host-owned shared-eye bridge was created, imported by the game, selected as the direct path, and produced DirectGPU frames.'
}
elseif($status -eq 'DXVK_HOST_OWNED_IMPORT_FAILED'){
    $lines+='interpretation=The OpenXR host reached the DXVK shared-eye bridge, but the game-side KMT eye import failed; inspect leftHr/rightHr and provider errors before pacing changes.'
}
elseif($status -eq 'DXVK_HOST_OWNED_BRIDGE_ALLOCATION_FAILED'){
    $lines+='interpretation=The OpenXR host failed to allocate/publish the host-owned shared-eye bridge; game-side import cannot succeed until host allocation is fixed.'
}
elseif($status -eq 'DXVK_HOST_OWNED_IMPORT_NOT_ESTABLISHED'){
    $lines+='interpretation=The host published a ready shared-eye bridge, but no matching game import was observed while gameplay fell back; inspect mapping visibility, generation identity and import eligibility.'
}
elseif($status -eq 'DXVK_SBS_FALLBACK_CONFIRMED'){
    $lines+='interpretation=DXVK loaded, but DirectGPU shared-eye transport did not activate; runtime fell back to SBS/Desktop Duplication.'
}
if($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){
    $lines+='interpretation_camera=Driver-seat camera code activated during a non-cockpit test slot.'
}
$lines|Set-Content (Join-Path $SessionDir 'AUTO_ANALYSIS_SUMMARY.txt') -Encoding UTF8
Write-Host ($lines -join [Environment]::NewLine)
