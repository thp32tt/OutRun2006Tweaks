param(
    [string]$GameExe = 'OR2006C2C.EXE',
    [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')]
    [string]$TestProfile = 'CORRECTNESS',
    [ValidateSet('Desktop','XR_NATIVE_2496X2688')]
    [string]$DX11SourceResolution = 'Desktop'
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
$hudProbe='0'
$r57Mode='0'
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
    'R56_01_ZERO'              { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='1'; $hudProbe='1' }
    'R56_02_SCALE35'           { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='2'; $hudProbe='2' }
    'R56_03_WORLD35'           { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='3'; $hudProbe='3' }
    'R56_04_RANKZERO'          { $semanticMode='3'; $hudExperimentMode='4'; $hudCoordMode='4'; $hudProbe='4' }
    'R56_05_POSITION_XP96'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='5' }
    'R56_06_POSITION_XM96'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='6' }
    'R56_07_POSITION_XS35'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='7' }
    'R56_08_POSITION_XCENTER'  { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='8' }
    'R56_09_RANK13_XP96'       { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='9' }
    'R56_10_RANK13_XM96'       { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='10' }
    'R56_11_RANK13_YM72'       { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='11' }
    'R56_12_RANK13_CENTER'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='12' }
    'R56_13_RANK46_XP96'       { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='13' }
    'R56_14_RANK46_YM72'       { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='14' }
    'R56_15_RANK46_CENTER'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='15' }
    'R56_16_RANK13_AS_HUD'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='16' }
    'R56_17_RANK46_AS_HUD'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='17' }
    'R56_18_RANK46_NEXTDRAW'   { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='18' }
    'R56_19_POSITION_NEXTDRAW' { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='19' }
    'R56_20_ALLSCREEN_RAW'     { $semanticMode='3'; $hudExperimentMode='2'; $hudProbe='20' }
    'R57_01_POSITION_KIND1_HUD35' { $semanticMode='0'; $hudExperimentMode='2'; $hudCoordMode='2'; $r57Mode='1' }
    'R57_02_POSITION_KIND0_HUD35' { $semanticMode='0'; $hudExperimentMode='2'; $hudCoordMode='2'; $r57Mode='2' }
    'R57_03_POSITION_ALL_WORLD35' { $semanticMode='0'; $hudExperimentMode='2'; $hudCoordMode='3'; $r57Mode='3' }
    'R57_04_RANK_ALL_AS_HUD'      { $semanticMode='0'; $hudExperimentMode='2'; $hudCoordMode='3'; $r57Mode='4' }
    'R57_05_RANK_PROJECTED_IPD'   { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='5' }
    'R57_06_RANK_PROJECTED_HEAD'  { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='6' }
    'R67_EYE_REPROJECT'           { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='6' }
    'R68_FIXPACK'                 { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='6' }
    'R69_FIXPACK'                 { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='6' }
    'R57_07_RANK_PROJECTED_13'    { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='7' }
    'R57_08_RANK_PROJECTED_46'    { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='8' }
    'R57_09_RANK_PROJECTED_ZERO'  { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='9' }
    'R57_10_RANK_PROJECTED_TRACE' { $semanticMode='0'; $hudExperimentMode='2'; $r57Mode='10' }
}
$oldExeSemanticMode=$env:OUTRUN_VR_EXE_SEMANTIC_MODE
$oldHudExperimentMode=$env:OUTRUN_VR_HUD_EXPERIMENT_MODE
$oldHudCoordMode=$env:OUTRUN_VR_HUD_COORD_MODE
$oldHudProbe=$env:OUTRUN_VR_HUD_PROBE
$oldR57Mode=$env:OUTRUN_VR_R57_MODE
$env:OUTRUN_VR_EXE_SEMANTIC_MODE=$semanticMode
$env:OUTRUN_VR_HUD_EXPERIMENT_MODE=$hudExperimentMode
$env:OUTRUN_VR_HUD_COORD_MODE=$hudCoordMode
$env:OUTRUN_VR_HUD_PROBE=$hudProbe
$env:OUTRUN_VR_R57_MODE=$r57Mode

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

$dx11SourceResolutionProfile='N/A'
$dx11SourceWidth=0
$dx11SourceHeight=0

if($backend -eq 'd3d9'){
    $profile=Get-OutRunVRTestProfile -Name $TestProfile
    $gameArgs=@($profile.Arguments)
}elseif($backend -eq 'dx11'){
    # 2026-10-04 Quest 3/VDXR evidence: a 90 Hz XR stream fed by a forced
    # 60 Hz game renderer produced a visible 60->90 3:2 repeat cadence
    # (roughly fresh=300/cached=150 per 450 XR frames). Make the DX11
    # development path XR-clock owned: keep simulation at 60 Hz, render on
    # xrWaitFrame cadence, and interpolate the intermediate render frames.
    $gameArgs=@(
        '-FramerateLimit=0',
        '-FramerateFastLoad=0',
        '-FramerateInterpolation=true',
        '-FramerateUnlockExperimental=true',
        '-FrameCadenceMode=1',
        '-FrameCadenceTargetHz=0',
        '-DisableDesktopVsync=true',
        '-TargetRefreshRateHz=0',
        '-SkyGlowFactor=1'
    )
    $dx11SourceResolutionProfile=$DX11SourceResolution
    if($DX11SourceResolution -eq 'XR_NATIVE_2496X2688'){
        # 2026-10-04 Quest 3/VDXR runtime evidence rejected the old B candidate.
        # 2496x2688 is a per-eye OpenXR target, not a valid game logical canvas:
        # feeding that portrait size into Game::screen_resolution stretches the
        # 4:3 menu/vehicle selector, collapses HUD coordinates toward centre and
        # increases game-side fill cost. Keep the HMD swapchain native in the
        # host, but preserve the desktop/game source aspect until a dedicated
        # offscreen eye-size path exists that does not mutate UI coordinates.
        Write-Warning 'XR_NATIVE_2496X2688 game-source override was runtime-rejected; using Desktop source aspect while OpenXR keeps its native eye swapchain.'
        $dx11SourceResolutionProfile='DESKTOP_ASPECT_SAFE_AFTER_XR_NATIVE_REJECT'
    }
    $profile=[ordered]@{
        Name=$TestProfile
        Description='DX11 primary path: XR-native cadence with 60 Hz simulation and interpolated render frames'
        Environment=[ordered]@{
            OUTRUN_VR_TEST_PROFILE=$TestProfile
            OUTRUN_VR_PERFORMANCE_PROFILE='1'
        }
    }
}else{
    # DXVK and other non-reference backends remain conservative until their
    # own runtime evidence justifies a cadence policy change.
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

# Keep expensive HUD stack-walk tracing out of normal play/performance runs.
# HUD-focused and stage-diagnostic profiles opt in explicitly.
$hudInspectorProfiles=@('HUD_SCREEN','HUD_MENU','HUD_WORLD','STAGE_DIAGNOSTIC')
if($backend -ne '2d' -and $hudInspectorProfiles -contains $TestProfile){
    $gameArgs += '-HudInspector=true'
}else{
    $gameArgs += '-HudInspector=false'
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
    "dx11SourceResolutionProfile=$dx11SourceResolutionProfile"
    "dx11SourceWidth=$dx11SourceWidth"
    "dx11SourceHeight=$dx11SourceHeight"
    "forceVrDisabled=$($backend -eq '2d')"
    "arguments=$($gameArgs -join ' ')"
    "exeSha256=$exeSha256"
    "exeSemanticIdentityVerified=$semanticIdentityVerified"
    "exeSemanticMode=$semanticMode"
    "hudExperimentMode=$hudExperimentMode"
    "hudCoordMode=$hudCoordMode"
    "hudProbe=$hudProbe"
    "r57Mode=$r57Mode"
)|Set-Content (Join-Path $sessionRoot 'RUN_OVERRIDES.txt') -Encoding UTF8
Write-Host "Runtime overrides: $($gameArgs -join ' ')"

$dxvkMode = $backend -eq 'dxvk-safe' -or $backend -eq 'dxvk'
$oldVkDisable = $env:VK_LOADER_LAYERS_DISABLE
$oldVkInstanceLayers = $env:VK_INSTANCE_LAYERS
$oldVkDebug = $env:VK_LOADER_DEBUG
$oldDxvkLogPath = $env:DXVK_LOG_PATH
$oldDxvkLogLevel = $env:DXVK_LOG_LEVEL
$oldVrForceDisabled = $env:OUTRUN_VR_FORCE_DISABLED
$oldTestProfile = $env:OUTRUN_VR_TEST_PROFILE
$oldPerformanceProfile = $env:OUTRUN_VR_PERFORMANCE_PROFILE
$oldShaderFingerprint = $env:OUTRUN_VR_SHADER_FINGERPRINT
$oldDx11Census = $env:OUTRUN_VR_DX11_CENSUS
$oldDx11CensusExhaustive = $env:OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE
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
    $sourceFile=Join-Path $root ("backends/{0}/SOURCE_SHA.txt" -f $(if($backend -eq '2d' -or $backend -eq 'dxvk-safe' -or $backend -eq 'dx11'){'d3d9'}else{$backend}))
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

# Expensive shader fingerprint capture and DX11 draw census are diagnostics,
# not part of the normal CORRECTNESS performance path.
if($backend -ne '2d' -and $TestProfile -eq 'STAGE_DIAGNOSTIC'){
    $env:OUTRUN_VR_SHADER_FINGERPRINT='1'
}else{
    $env:OUTRUN_VR_SHADER_FINGERPRINT=$null
}
if($backend -eq 'dx11' -and $TestProfile -eq 'STAGE_DIAGNOSTIC'){
    $env:OUTRUN_VR_DX11_CENSUS='1'
}else{
    $env:OUTRUN_VR_DX11_CENSUS='0'
}
$env:OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE='0'

foreach($entry in $profile.Environment.GetEnumerator()){
    Set-Item -Path ("Env:" + $entry.Key) -Value ([string]$entry.Value)
}

if($dxvkMode){
    $env:VK_LOADER_LAYERS_DISABLE='~implicit~'
    $env:VK_INSTANCE_LAYERS=$null
    $env:VK_LOADER_DEBUG='error,warn,layer'
    $env:DXVK_LOG_PATH=$sessionRoot
    $env:DXVK_LOG_LEVEL='info'
    $bandicam=Get-Process -ErrorAction SilentlyContinue|Where-Object{
        $_.ProcessName -match '^bdcam' -or $_.ProcessName -match 'bandicam'
    }
    if($bandicam){
        Write-Warning 'Bandicam process detected. Vulkan implicit layers are disabled for this launch; close Bandicam too if DXVK still crashes.'
    }
}

$gameExitCode=0
try{
    $p=Start-Process -FilePath $game -ArgumentList $gameArgs -WorkingDirectory $root -PassThru
    $p.WaitForExit()
    $gameExitCode=$p.ExitCode
} finally {
    $env:OUTRUN_VR_FORCE_DISABLED=$oldVrForceDisabled
    $env:OUTRUN_VR_TEST_PROFILE=$oldTestProfile
    $env:OUTRUN_VR_PERFORMANCE_PROFILE=$oldPerformanceProfile
    $env:OUTRUN_VR_SHADER_FINGERPRINT=$oldShaderFingerprint
    $env:OUTRUN_VR_DX11_CENSUS=$oldDx11Census
    $env:OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE=$oldDx11CensusExhaustive
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED=$oldExeSemanticVerified
    $env:OUTRUN_VR_EXE_SEMANTIC_MODE=$oldExeSemanticMode
    $env:OUTRUN_VR_HUD_EXPERIMENT_MODE=$oldHudExperimentMode
    $env:OUTRUN_VR_HUD_COORD_MODE=$oldHudCoordMode
    $env:OUTRUN_VR_HUD_PROBE=$oldHudProbe
    $env:OUTRUN_VR_R57_MODE=$oldR57Mode
    foreach($key in $identityKeys){
        [Environment]::SetEnvironmentVariable($key,$oldIdentity[$key],'Process')
    }
    if($dxvkMode){
        $env:VK_LOADER_LAYERS_DISABLE=$oldVkDisable
        $env:VK_INSTANCE_LAYERS=$oldVkInstanceLayers
        $env:VK_LOADER_DEBUG=$oldVkDebug
        $env:DXVK_LOG_PATH=$oldDxvkLogPath
        $env:DXVK_LOG_LEVEL=$oldDxvkLogLevel
    }
}

$deadline=(Get-Date).AddSeconds(15)
do{
    $hostProc=Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue
    if(!$hostProc){break}
    Start-Sleep -Milliseconds 500
}while((Get-Date) -lt $deadline)

if(Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue){
    Write-Warning 'outrun-vr-host.exe remained after game exit; closing this test host automatically so log collection can finish.'
    Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 750
}
if(Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue){
    throw 'Could not close outrun-vr-host.exe automatically; log collection was not started.'
}

& $collector
if($LASTEXITCODE -and $LASTEXITCODE -ne 0){exit $LASTEXITCODE}
if($gameExitCode -ne 0){
    Write-Warning ("OR2006C2C.EXE exited with code {0}; diagnostic collection completed before propagating failure." -f $gameExitCode)
    exit $gameExitCode
}
exit 0