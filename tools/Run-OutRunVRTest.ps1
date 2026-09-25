param(
    [string]$GameExe = 'OR2006C2C.EXE',
    [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')]
    [string]$TestProfile = 'CORRECTNESS'
)

$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$active=Join-Path $root 'ACTIVE_VR_BACKEND.txt'
$current=Join-Path $root 'CURRENT_VR_SESSION.json'
$collector=Join-Path $root 'Collect-OutRunVRLogs.ps1'
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$profileLib=Join-Path $root 'OutRunVR-TestProfiles.ps1'
$game=Join-Path $root $GameExe

# Canonical EXE identity gates the reverse-engineered HUD semantic map.
# Never apply hard-coded RVA semantics to an unknown executable.
$canonicalExeSha256='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
$exeSha256='missing'
$semanticIdentityVerified=$false
try{
    if(Test-Path $game){
        $exeSha256=(Get-FileHash $game -Algorithm SHA256).Hash.ToLowerInvariant()
        $semanticIdentityVerified=($exeSha256 -eq $canonicalExeSha256)
    }
}catch{
    $semanticIdentityVerified=$false
}
$oldExeSemanticVerified=$env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED
if($semanticIdentityVerified){
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED='1'
}else{
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED=$null
}

if(!(Test-Path $active) -or !(Test-Path $current)){
    throw 'Select a renderer/backend once before using the test launcher.'
}
if(!(Test-Path $collector)){throw 'Collect-OutRunVRLogs.ps1 not found.'}
if(!(Test-Path $selector)){throw 'Select-OutRunVRBackend.ps1 not found.'}
if(!(Test-Path $profileLib)){throw 'OutRunVR-TestProfiles.ps1 not found.'}
if(!(Test-Path $game)){throw "Game executable not found: $game"}
. $profileLib

$running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if($running){throw 'OutRun or outrun-vr-host.exe is already running.'}

$kv=@{}
Get-Content $active|ForEach-Object{if($_ -match '^([^=]+)=(.*)$'){$kv[$matches[1]]=$matches[2]}}
$backend=$kv.backend
if(!$backend){throw 'Active backend identity is missing.'}
$variant=if($kv.variant){[string]$kv.variant}else{'AUTO'}
$semanticMode='0'
$hudExperimentMode='0'
$hudCoordMode='0'
$producerMode='0'
switch($variant){
    'X_SCREEN_HUD'       { $semanticMode='1' }
    'X_WORLD_RANK'       { $semanticMode='2' }
    'X_COMBINED'         { $semanticMode='3' }
    'R54_A_NEXTDRAW'     { $semanticMode='3'; $hudExperimentMode='1' }
    'R54_B_STICKY'       { $semanticMode='3'; $hudExperimentMode='2' }
    'R54_C_FULL_OWNER'   { $semanticMode='3'; $hudExperimentMode='3' }
    'R54_D_HUD_PLANE'    { $semanticMode='3'; $hudExperimentMode='4' }
    'R55_A_ZERO'         { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='1' }
    'R55_B_SCALE35'      { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='2' }
    'R55_C_WORLD35'      { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='3' }
    'R55_D_RANKZERO'     { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='4' }
    'R56_A_DISPRANK35'   { $semanticMode='3'; $hudExperimentMode='4'; $producerMode='1' }
    'R56_B_RANK_BASECAM' { $semanticMode='3'; $hudExperimentMode='4'; $producerMode='2' }
    'R56_C_RANKCLIP35'   { $semanticMode='3'; $hudExperimentMode='4'; $producerMode='3' }
    'R56_D_COMBINED'     { $semanticMode='3'; $hudExperimentMode='4'; $producerMode='4' }
}
$oldExeSemanticMode=$env:OUTRUN_VR_EXE_SEMANTIC_MODE
$oldHudExperimentMode=$env:OUTRUN_VR_HUD_EXPERIMENT_MODE
$oldHudCoordMode=$env:OUTRUN_VR_HUD_COORD_MODE
$oldProducerMode=$env:OUTRUN_VR_PRODUCER_MODE
$env:OUTRUN_VR_EXE_SEMANTIC_MODE=$semanticMode
$env:OUTRUN_VR_HUD_EXPERIMENT_MODE=$hudExperimentMode
$env:OUTRUN_VR_HUD_COORD_MODE=$hudCoordMode
$env:OUTRUN_VR_PRODUCER_MODE=$producerMode

$patterns=@(
    'OutRun2006Tweaks*.log',
    'OutRun2006Tweaks-hudtrace*.csv',
    'OutRun2006Tweaks-xstmap*.csv',
    'outrun-vr-host*.log',
    'outrun-vr-host-pipeline*.log',
    'outrun-vr-watchdog*.log',
    'backend*.log',
    'OR2006C2C_d3d9.log',
    'OR2006C2C_dxgi.log',
    'OR2006C2C_d3d11.log',
    'OR2006C2C_vkd3d*.log',
    'dxvk*.log',
    'vkd3d*.log',
    'crash.log',
    'OR2006C2C.EXE.*.zip',
    '*.dmp'
)
$stale=$false
foreach($pattern in $patterns){
    if(Get-ChildItem $root -Filter $pattern -File -ErrorAction SilentlyContinue|Select-Object -First 1){
        $stale=$true
        break
    }
}
if($stale){
    & $selector -Backend $backend -TestProfile $TestProfile -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw 'Failed to seal stale logs before launch.'}
}

$state=Get-Content $current -Raw|ConvertFrom-Json
if($state.TestProfile -and $state.TestProfile -ne $TestProfile){
    & $selector -Backend $backend -TestProfile $TestProfile -VariantId $variant
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw 'Failed to prepare requested test profile.'}
    $state=Get-Content $current -Raw|ConvertFrom-Json
}

Write-Host "Starting test session: $($state.SessionId)"
Write-Host "Backend: $backend"
Write-Host "Profile: $TestProfile"

if($backend -eq 'd3d9'){
    $profile=Get-OutRunVRTestProfile -Name $TestProfile
    $gameArgs=@($profile.Arguments)
}else{
    # Non-DX9Ex backends are retained only for explicit legacy comparison.
    # Keep them on the conservative startup policy until the DX9Ex reference is accepted.
    $gameArgs=@(
        '-FramerateLimit=60',
        '-FramerateFastLoad=0',
        '-FramerateInterpolation=false',
        '-FramerateUnlockExperimental=false',
        '-FrameCadenceMode=0',
        '-FrameCadenceTargetHz=0',
        '-DisableDesktopVsync=false',
        '-TargetRefreshRateHz=0',
        '-SkyGlowFactor=1'
    )
    $profile=[ordered]@{
        Name=$TestProfile
        Description='Legacy/non-reference backend conservative launch'
        Environment=[ordered]@{
            OUTRUN_VR_TEST_PROFILE=$TestProfile
            OUTRUN_VR_PERFORMANCE_PROFILE='0'
        }
    }
}

if($backend -ne '2d'){
    $gameArgs += '-HudInspector=true'
}

$sessionRoot=Join-Path $root ("logs/{0}/{1}/{2}/{3}" -f $state.BuildMatrixId,$state.VariantId,$TestProfile,$state.SessionId)
New-Item -ItemType Directory -Force $sessionRoot|Out-Null

$assetAnalyzer=Join-Path $root 'tools/analyze_outrun_assets.py'
if(!(Test-Path $assetAnalyzer)){
    $assetAnalyzer=Join-Path $root 'analyze_outrun_assets.py'
}
$pythonCmd=Get-Command python -ErrorAction SilentlyContinue
if($pythonCmd -and (Test-Path $assetAnalyzer)){
    $assetOut=Join-Path $sessionRoot 'VR_ASSET_SEMANTICS.json'
    try {
        & $pythonCmd.Source $assetAnalyzer --root $root --output $assetOut --max-files 5000 --quiet
        $assetExitCode=$LASTEXITCODE
        if(Test-Path $assetOut){
            try {
                $assetReport=Get-Content $assetOut -Raw|ConvertFrom-Json
                if($assetReport.status -ne 'COMPLETE'){
                    Write-Warning ("Asset semantic inventory is {0}: scanned {1}/{2}, parseErrors={3}" -f $assetReport.status,$assetReport.files_scanned,$assetReport.discovered_candidates,$assetReport.parse_error_count)
                }
            } catch {
                Write-Warning "Asset semantic inventory status could not be parsed: $($_.Exception.Message)"
            }
        }
        if($assetExitCode -ne 0){ Write-Warning "Asset semantic analyzer exited with code $assetExitCode" }
    } catch {
        Write-Warning "Asset semantic analyzer failed: $($_.Exception.Message)"
    }
}

@(
    "backend=$backend"
    "profile=$TestProfile"
    "forceVrDisabled=$($backend -eq '2d')"
    "arguments=$($gameArgs -join ' ')"
    "exeSha256=$exeSha256"
    "exeSemanticIdentityVerified=$semanticIdentityVerified"
    "exeSemanticMode=$semanticMode"
    "hudExperimentMode=$hudExperimentMode"
    "hudCoordMode=$hudCoordMode"
    "producerMode=$producerMode"
)|Set-Content (Join-Path $sessionRoot 'RUN_OVERRIDES.txt') -Encoding UTF8
Write-Host "Runtime overrides: $($gameArgs -join ' ')"

$dxvkMode = $backend -eq 'dxvk-safe' -or $backend -eq 'dxvk'
$oldVkDisable = $env:VK_LOADER_LAYERS_DISABLE
$oldVkInstanceLayers = $env:VK_INSTANCE_LAYERS
$oldVkDebug = $env:VK_LOADER_DEBUG
$oldVrForceDisabled = $env:OUTRUN_VR_FORCE_DISABLED
$oldTestProfile = $env:OUTRUN_VR_TEST_PROFILE
$oldPerformanceProfile = $env:OUTRUN_VR_PERFORMANCE_PROFILE
$oldShaderFingerprint = $env:OUTRUN_VR_SHADER_FINGERPRINT
$identityKeys = @(
    'OUTRUN_VR_SESSION_ID',
    'OUTRUN_VR_VARIANT_ID',
    'OUTRUN_VR_MATRIX_ID',
    'OUTRUN_VR_BACKEND',
    'OUTRUN_VR_CONFIG_SHA256',
    'OUTRUN_VR_SOURCE_SHA'
)
$oldIdentity = @{}
foreach($key in $identityKeys){ $oldIdentity[$key] = [Environment]::GetEnvironmentVariable($key,'Process') }

$sourceSha=if($state.SourceSha){[string]$state.SourceSha}else{'unknown'}
if($sourceSha -eq 'unknown'){
    $sourceFile=Join-Path $root ("backends/{0}/SOURCE_SHA.txt" -f $(if($backend -eq '2d' -or $backend -eq 'dxvk-safe'){'d3d9'}else{$backend}))
    if(Test-Path $sourceFile){ $sourceSha=(Get-Content $sourceFile -Raw).Trim() }
}
$env:OUTRUN_VR_SESSION_ID=[string]$state.SessionId
$env:OUTRUN_VR_VARIANT_ID=[string]$state.VariantId
$env:OUTRUN_VR_MATRIX_ID=[string]$state.BuildMatrixId
$env:OUTRUN_VR_BACKEND=[string]$backend
$env:OUTRUN_VR_CONFIG_SHA256=[string]$state.ConfigSha256
$env:OUTRUN_VR_SOURCE_SHA=$sourceSha

if($backend -eq '2d'){
    $env:OUTRUN_VR_FORCE_DISABLED='1'
    Write-Host '2D control isolation: all OpenXR/VR hook installers are disabled for this process.'
}else{
    $env:OUTRUN_VR_FORCE_DISABLED=$null
}

if($backend -ne '2d'){
    $env:OUTRUN_VR_SHADER_FINGERPRINT='1'
}else{
    $env:OUTRUN_VR_SHADER_FINGERPRINT=$null
}

foreach($entry in $profile.Environment.GetEnumerator()){
    Set-Item -Path ("Env:" + $entry.Key) -Value ([string]$entry.Value)
}

if($dxvkMode){
    $env:VK_LOADER_LAYERS_DISABLE='~implicit~'
    $env:VK_INSTANCE_LAYERS=$null
    $env:VK_LOADER_DEBUG='error,warn,layer'
    $bandicam=Get-Process -ErrorAction SilentlyContinue|Where-Object{
        $_.ProcessName -match '^bdcam' -or $_.ProcessName -match 'bandicam'
    }
    if($bandicam){
        Write-Warning 'Bandicam process detected. Vulkan implicit layers are disabled for this launch; close Bandicam too if DXVK still crashes.'
    }
}

try{
    $p=Start-Process -FilePath $game -ArgumentList $gameArgs -WorkingDirectory $root -PassThru
    $p.WaitForExit()
} finally {
    $env:OUTRUN_VR_FORCE_DISABLED=$oldVrForceDisabled
    $env:OUTRUN_VR_TEST_PROFILE=$oldTestProfile
    $env:OUTRUN_VR_PERFORMANCE_PROFILE=$oldPerformanceProfile
    $env:OUTRUN_VR_SHADER_FINGERPRINT=$oldShaderFingerprint
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED=$oldExeSemanticVerified
    $env:OUTRUN_VR_EXE_SEMANTIC_MODE=$oldExeSemanticMode
    $env:OUTRUN_VR_HUD_EXPERIMENT_MODE=$oldHudExperimentMode
    $env:OUTRUN_VR_HUD_COORD_MODE=$oldHudCoordMode
    $env:OUTRUN_VR_PRODUCER_MODE=$oldProducerMode
    foreach($key in $identityKeys){
        [Environment]::SetEnvironmentVariable($key,$oldIdentity[$key],'Process')
    }
    if($dxvkMode){
        $env:VK_LOADER_LAYERS_DISABLE=$oldVkDisable
        $env:VK_INSTANCE_LAYERS=$oldVkInstanceLayers
        $env:VK_LOADER_DEBUG=$oldVkDebug
    }
}

$deadline=(Get-Date).AddSeconds(15)
do{
    $hostProc=Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue
    if(!$hostProc){break}
    Start-Sleep -Milliseconds 500
}while((Get-Date) -lt $deadline)

if(Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue){
    Write-Warning 'outrun-vr-host.exe is still running. Close it, then run Collect-OutRunVRLogs.cmd once. No logs were deleted.'
    exit 2
}

& $collector
if($LASTEXITCODE -and $LASTEXITCODE -ne 0){exit $LASTEXITCODE}