param(
    [string]$GameExe = 'OR2006C2C.EXE',
    [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC','COCKPIT_PARTICLES','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')]
    [string]$TestProfile = 'CORRECTNESS',
    [ValidateSet('OFF','ON')]
    [string]$GpuDiagnostics = 'OFF',
    [ValidateSet('DEFAULT','1.00','1.15','1.30')][string]$CockpitVehicleScale = 'DEFAULT',
    [ValidateSet('DEFAULT','NATIVE','CAR')][string]$CockpitCameraBasis = 'DEFAULT',
    [ValidateSet('DEFAULT','0.20','0.30','0.50','0.80')][string]$CockpitGlassProbeOpacity = 'DEFAULT',
    [ValidateSet('DEFAULT','ON','OFF')][string]$GpuLabTransparency = 'DEFAULT',
    [ValidateSet('DEFAULT','512','1024')][string]$GpuLabReflection = 'DEFAULT',
    [ValidateSet('DEFAULT','0','4')][string]$GpuLabSkyGlow = 'DEFAULT',
    [ValidateSet('DEFAULT','ON','OFF')][string]$GpuLabCulling = 'DEFAULT',
    [ValidateSet('DEFAULT','OFF','2X','4X')][string]$GpuLabMsaa = 'DEFAULT',
    [ValidateSet('NONE','WATERFRONT','SAND_SPRAY','DENSE_BUILDINGS','OTHER')][string]$GpuLabScene = 'NONE'
)

$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

# GUI starts this script in a hidden PowerShell child. Without an explicit
# failure channel, a missing EXE, wrong binary hash, or copy/launch exception
# causes a silent return to the minimized selector and looks like "no launch".
# A successful session remains noninteractive; only failures show a dialog.
trap {
    $launchError = ($_ | Out-String).Trim()
    $errorFile = Join-Path $root 'OUTRUNVR_LAUNCH_ERROR.txt'
    $details = "UTC=$((Get-Date).ToUniversalTime().ToString('o'))" +
        [Environment]::NewLine + "TASK=CONVERSION-DX9EX-00783" +
        [Environment]::NewLine + $launchError
    try { Set-Content -LiteralPath $errorFile -Value $details -Encoding UTF8 } catch {}
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show(
            "OutRun DX9Ex launch failed. See OUTRUNVR_LAUNCH_ERROR.txt in the game folder." +
            [Environment]::NewLine + $launchError,
            "OutRun VR launch error")
    } catch { Write-Host $details }
    exit 1
}
$active=Join-Path $root 'ACTIVE_VR_BACKEND.txt'
$current=Join-Path $root 'CURRENT_VR_SESSION.json'
$collector=Join-Path $root 'Collect-OutRunVRLogs.ps1'
$selector=Join-Path $root 'Select-OutRunVRBackend.ps1'
$profileLib=Join-Path $root 'OutRunVR-TestProfiles.ps1'
$game=Join-Path $root $GameExe

# A clean PC Fast Test ZIP cannot carry a machine-specific selected
# renderer or CURRENT_VR_SESSION.json. Bootstrap only a genuinely new DX9Ex
# install; never silently replace a user's existing 2D/DXVK selection.
# Validate the original game and scripts BEFORE trying to install any DLL.
if(!(Test-Path $collector)){throw 'Collect-OutRunVRLogs.ps1 not found.'}
if(!(Test-Path $selector)){throw 'Select-OutRunVRBackend.ps1 not found.'}
if(!(Test-Path $profileLib)){throw 'OutRunVR-TestProfiles.ps1 not found.'}
if(!(Test-Path $game)){throw "Game executable not found: $game"}
if(!(Test-Path -LiteralPath (Join-Path $root 'OutRun2006Tweaks.ini'))){throw 'INI missing; extract full ZIP into the game folder.'}
. $profileLib

$running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if($running){throw 'OutRun or outrun-vr-host.exe is already running.'}

$activeMissing = !(Test-Path -LiteralPath $active)
$currentMissing = !(Test-Path -LiteralPath $current)
if($activeMissing -or $currentMissing){
    if(-not ($activeMissing -and $currentMissing)){
        throw 'Incomplete VR backend session (one metadata file missing). Run Select-OutRunVRBackend.ps1 -Backend d3d9 -TestProfile CORRECTNESS to repair it explicitly.'
    }
    $firstRunPayload = Join-Path $root 'backends/d3d9'
    foreach($required in @('dinput8.dll','outrun-vr-host.exe','SOURCE_SHA.txt')){
        if(!(Test-Path -LiteralPath (Join-Path $firstRunPayload $required))){
            throw "DX9Ex first-run payload missing $required in $firstRunPayload. Extract the complete PC Fast Test ZIP into the original OR2006C2C.EXE game folder."
        }
    }
    Write-Host 'PC FAST FIRST LAUNCH: selecting DX9Ex/CURRENT_FOCUS and creating the initial VR session.'
    & $selector -Backend d3d9 -TestProfile $TestProfile -VariantId CURRENT_FOCUS
    if(-not $? -or !(Test-Path -LiteralPath $active) -or
       !(Test-Path -LiteralPath $current)){
        throw 'DX9Ex first-run setup failed to produce ACTIVE_VR_BACKEND.txt and CURRENT_VR_SESSION.json.'
    }
}

$kv=@{}
Get-Content $active|ForEach-Object{if($_ -match '^([^=]+)=(.*)$'){$kv[$matches[1]]=$matches[2]}}
$backend=$kv.backend
if(!$backend){throw 'Active backend identity is missing.'}
if($backend -eq 'd3d9'){
  foreach($required in @('dinput8.dll','outrun-vr-host.exe')){
    if(!(Test-Path -LiteralPath (Join-Path $root $required))){throw "Installed DX9Ex backend missing $required in game folder."}
  }
}
$variant=if($kv.variant){[string]$kv.variant}else{'AUTO'}

# Packages are commonly extracted over an older test directory. Treat session
# metadata from a different build matrix as stale and let the current selector
# migrate its legacy VariantId instead of failing parameter validation.
$packageMatrixFile=Join-Path $root 'BUILD_MATRIX_ID.txt'
$packageMatrix=if(Test-Path $packageMatrixFile){(Get-Content $packageMatrixFile -Raw).Trim()}else{''}

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
$state=$null
try{$state=Get-Content $current -Raw|ConvertFrom-Json}catch{$state=$null}
$matrixMismatch=$false
if($packageMatrix){
    $matrixMismatch=(-not $state) -or (-not $state.BuildMatrixId) -or ([string]$state.BuildMatrixId -ne $packageMatrix)
}
$profileMismatch=(-not $state) -or (-not $state.TestProfile) -or ([string]$state.TestProfile -ne $TestProfile)
$backendMismatch=(-not $state) -or (-not $state.Backend) -or ([string]$state.Backend -ne $backend)

if($stale -or $matrixMismatch -or $profileMismatch -or $backendMismatch){
    & $selector -Backend $backend -TestProfile $TestProfile -VariantId $variant
    if (-not $?) { throw 'Failed to prepare current test session.' }
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
        '-SkyGlowFactor=4'
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

# Quest3 2026-10-17: transient car matrix_B0 eligibility can alternate
# between car-space and native-camera basis, causing severe zoom/seat jumps.
# Use ONE uninterrupted native-camera basis for all normal cockpit probes.
# Explicit CAR is retained for developer-only side-by-side investigation.
if($CockpitCameraBasis -ne 'DEFAULT' -and
   ($backend -ne 'd3d9' -or $TestProfile -ne 'COCKPIT_PARTICLES')){
    throw 'Cockpit camera basis override requires DX9Ex COCKPIT_PARTICLES.'
}
$cockpitEffectiveBasis='DEFAULT'
if($backend -eq 'd3d9' -and $TestProfile -eq 'COCKPIT_PARTICLES'){
    $cockpitEffectiveBasis=if($CockpitCameraBasis -eq 'CAR'){'CAR'}else{'NATIVE'}
    $gameArgs=@($gameArgs|Where-Object{$_ -notmatch '^-DriverSeatCarSpaceBasis='})
    $cameraBasisArg=if($cockpitEffectiveBasis -eq 'CAR'){
        '-DriverSeatCarSpaceBasis=true'
    }else{
        '-DriverSeatCarSpaceBasis=false'
    }
    $gameArgs+=$cameraBasisArg
}

# A/B/C cockpit presets are runtime settings, never original EXE/PMT edits.
# Each session records the exact choice; glass opacity is diagnostic only until
# the real PC windshield material has been positively identified.
if($CockpitVehicleScale -ne 'DEFAULT' -or $CockpitGlassProbeOpacity -ne 'DEFAULT'){
    if($backend -ne 'd3d9' -or $TestProfile -ne 'COCKPIT_PARTICLES'){
        throw 'Cockpit scale/glass probes require DX9Ex COCKPIT_PARTICLES.'
    }
    if($CockpitVehicleScale -ne 'DEFAULT'){
        $gameArgs=@($gameArgs|Where-Object{$_ -notmatch '^-DriverSeatVehicleScale='})
        $gameArgs+='-DriverSeatVehicleScale='+$CockpitVehicleScale
    }
    if($CockpitGlassProbeOpacity -ne 'DEFAULT'){
        $gameArgs=@($gameArgs|Where-Object{$_ -notmatch '^-DriverSeatGlassOpacity='})
        $gameArgs+='-DriverSeatGlassOpacity='+$CockpitGlassProbeOpacity
        $gameArgs+='-DriverSeatGlassMaterialTrace=true'
    }
}

# The measured C preset may run WITHOUT the GPU-Lab instrumentation. Other
# A/B diagnostic combinations still require GPU Diagnostics ON; they are not
# silently promoted to gameplay defaults.
$gpuLabValues=@($GpuLabTransparency,$GpuLabReflection,$GpuLabSkyGlow,$GpuLabCulling)
$gpuLabActive=@($gpuLabValues|Where-Object{$_ -ne 'DEFAULT'}).Count -gt 0
$measuredCProduction=($backend -eq 'd3d9' -and $GpuDiagnostics -eq 'OFF' -and
    $gpuLabActive -and $GpuLabTransparency -eq 'OFF' -and
    $GpuLabReflection -eq '1024' -and $GpuLabSkyGlow -eq '4' -and
    $GpuLabCulling -eq 'ON' -and
    $GpuLabMsaa -in @('4X','DEFAULT'))
if($gpuLabActive){
    if($backend -ne 'd3d9' -or
        @($gpuLabValues|Where-Object{$_ -eq 'DEFAULT'}).Count -gt 0 -or
        ($GpuDiagnostics -ne 'ON' -and -not $measuredCProduction)){
        throw 'GPU lab A/B needs DX9Ex diagnostics ON; production OFF is supported only for measured C (culling ON, SSAA OFF, reflection 1024, SkyGlow 4, MSAA 4X).'
    }
    $helper=Join-Path $root 'OutRunVR-GPU-Lab-Settings.ps1'
    if(!(Test-Path -LiteralPath $helper)){throw 'GPU lab settings helper missing'}
    . $helper
    $msaa = if($GpuLabMsaa -eq 'DEFAULT'){'4X'}else{$GpuLabMsaa}
    $gameArgs=@(Set-OutRunVRGpuLabArguments -BaseArgs $gameArgs `
        -Transparency $GpuLabTransparency -Reflection $GpuLabReflection `
        -SkyGlow $GpuLabSkyGlow -StageCulling $GpuLabCulling -Msaa $msaa)
}
if($backend -ne '2d'){
    # The optional C gameplay preset must not force per-draw HUD inspector
    # overhead. Keep HUD Inspector ON for all existing diagnostic sessions.
    $gameArgs += if($measuredCProduction){'-HudInspector=false'}else{'-HudInspector=true'}
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
    "gpuDiagnostics=$GpuDiagnostics"
    "cockpitVehicleScale=$CockpitVehicleScale"
    "cockpitCameraBasis=$cockpitEffectiveBasis"
    "cockpitGlassProbeOpacity=$CockpitGlassProbeOpacity"
    "cockpitGlassActualTransparency=NOT_IMPLEMENTED"
    "gpuLabTransparency=$GpuLabTransparency"
    "gpuLabReflection=$GpuLabReflection"
    "gpuLabSkyGlow=$GpuLabSkyGlow"
    "gpuLabCulling=$GpuLabCulling"
    "gpuLabMsaa=$GpuLabMsaa"
    "gpuLabScene=$GpuLabScene"
    "cockpitParticleExperiment=$($backend -eq 'd3d9' -and $TestProfile -eq 'COCKPIT_PARTICLES')"
    "particleRingRequiresVerifiedWorldParticleDraw=true"
    "cockpitGlassAssetInjection=NOT_SUPPORTED_BY_THIS_PROFILE"
    "gpuLabSSAAExpectedGate=$(if($gpuLabActive){$GpuLabTransparency}else{'UNSPECIFIED'})"
    "gpuLabSSAAValidation=CHECK_VR_GPU_LAB_SSAA_GATE_AND_DEVICE_LINES"
    "forceVrDisabled=$($backend -eq '2d')"
    "arguments=$($gameArgs -join ' ')"
)|Set-Content (Join-Path $sessionRoot 'RUN_OVERRIDES.txt') -Encoding UTF8
Write-Host "Runtime overrides: $($gameArgs -join ' ')"

$dxvkMode = $backend -eq 'dxvk-safe' -or $backend -eq 'dxvk'
$oldVkDisable = $env:VK_LOADER_LAYERS_DISABLE
$oldVkInstanceLayers = $env:VK_INSTANCE_LAYERS
$oldVkDebug = $env:VK_LOADER_DEBUG
$oldVrForceDisabled = $env:OUTRUN_VR_FORCE_DISABLED
$oldGpuProfiling = $env:OUTRUN_VR_GPU_PROFILE
$oldPacingDiagnostics = $env:OUTRUN_VR_PACING_DIAGNOSTICS
$oldGpuScene = $env:OUTRUN_VR_GPU_SCENE
$oldTestProfile = $env:OUTRUN_VR_TEST_PROFILE
$oldPerformanceProfile = $env:OUTRUN_VR_PERFORMANCE_PROFILE
$oldParticleGpuUpload = $env:OUTRUN_VR_R30_PARTICLE_VB
$oldShaderFingerprint = $env:OUTRUN_VR_SHADER_FINGERPRINT
$oldExeSemanticsVerified = $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED
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

# HUD/world semantic promotion is valid only for the pinned canonical EXE.
# Establish the gate before process creation so the runtime inspector and
# renderer see the same identity decision as the post-run collector.
$canonicalExeSha='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
$launchExeSha=(Get-FileHash $game -Algorithm SHA256).Hash.ToLowerInvariant()
if($backend -ne '2d' -and $launchExeSha -ne $canonicalExeSha){
    throw "VR semantic identity mismatch before launch. Expected $canonicalExeSha, got $launchExeSha"
}
if($backend -ne '2d'){
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED='1'
}else{
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED=$null
}

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

# Never leak an inherited experimental draw flag into CORRECTNESS or
# rollback slots. The selected profile is the only activation authority.
$env:OUTRUN_VR_R30_PARTICLE_VB = $null
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

# The shipped slot selector uses one optional checkbox, never a required
# manually entered environment variable. OFF is the safe gameplay default.
# ON enables nonblocking D3D9 GPU timestamps + XR/CPU pacing + nvidia-smi.
if ($GpuDiagnostics -eq 'ON' -and $backend -ne 'd3d9') {
    throw 'GPU detailed profiling is supported only by the DX9Ex game backend.'
}
$gpuDiagnosticActive = ($backend -eq 'd3d9' -and $GpuDiagnostics -eq 'ON')
$env:OUTRUN_VR_GPU_PROFILE = if ($gpuDiagnosticActive) { '1' } else { $null }
$env:OUTRUN_VR_GPU_SCENE = if ($gpuDiagnosticActive -and $GpuLabScene -ne 'NONE') {
    $GpuLabScene
} else { $null }
if ($gpuDiagnosticActive) {
    $env:OUTRUN_VR_PACING_DIAGNOSTICS = '1'
} elseif ($measuredCProduction) {
    # An inherited diagnostic environment must not defeat no-profiling mode.
    $env:OUTRUN_VR_PACING_DIAGNOSTICS = $null
}
Write-Host "GPU detailed diagnostics: $GpuDiagnostics (D3D9 timestamps / pacing / whole-GPU sampler)"
# Opt-in whole-GPU telemetry accompanies the QPC pacing session. The external
# nvidia-smi process samples NVIDIA's driver once per second and does not run
# any D3D9/OpenXR hooks or block the game process.
$gpuCaptureRequested = ($backend -eq 'd3d9' -and $env:OUTRUN_VR_PACING_DIAGNOSTICS -eq '1')
$gpuCaptureStatus = 'NOT_REQUESTED'
$gpuCaptureStartedUtc = $null
$gpuSampler = $null
$gpuCsv = Join-Path $sessionRoot 'outrun-vr-gpu-utilization.csv'
if ($gpuCaptureRequested) {
    $gpuCaptureStatus = 'NVIDIA_SMI_UNAVAILABLE'
    $smiCommand = Get-Command 'nvidia-smi.exe' -CommandType Application -ErrorAction SilentlyContinue
    $smiPath = if ($smiCommand) { $smiCommand.Source } else { $null }
    if (-not $smiPath -and $env:ProgramFiles) {
        $candidate = Join-Path $env:ProgramFiles 'NVIDIA Corporation\NVSMI\nvidia-smi.exe'
        if (Test-Path -LiteralPath $candidate) { $smiPath = $candidate }
    }
    if ($smiPath) {
        # Quote the filename inside ArgumentList: installation paths can contain spaces.
        $smiArguments = @(
            '--query-gpu=timestamp,index,utilization.gpu,utilization.memory,memory.used,temperature.gpu',
            '--format=csv',
            '--loop=1',
            ('--filename="{0}"' -f $gpuCsv)
        )
        try {
            $gpuCaptureStartedUtc = (Get-Date).ToUniversalTime().ToString('o')
            $gpuSampler = Start-Process -FilePath $smiPath -ArgumentList $smiArguments -PassThru -WindowStyle Hidden -ErrorAction Stop
            $gpuCaptureStatus = 'SAMPLING'
            Write-Host "GPU sampling: $gpuCsv (NVIDIA whole-GPU, 1 second)"
        } catch {
            $gpuCaptureStatus = 'START_FAILED'
            Write-Warning "GPU telemetry unavailable; game continues normally: $($_.Exception.Message)"
        }
    } else {
        Write-Warning 'nvidia-smi.exe not found; GPU utilization cannot be recorded on this PC.'
    }
}

# Prewarm OpenXR without waiting for the host to become ready.
# Use the same configuration environment as VRLaunchHostOnce in the game.
if ($backend -eq 'd3d9') {
    $xrHost = Join-Path $root 'outrun-vr-host.exe'
    if ((Test-Path -LiteralPath $xrHost) -and
        -not (Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue)) {
        $vrValues = @{}
        $inVr = $false
        foreach ($line in (Get-Content (Join-Path $root 'OutRun2006Tweaks.ini') -ErrorAction SilentlyContinue)) {
            if ($line -match '^\s*\[([^]]+)\]\s*$') {
                $inVr = ($matches[1] -ieq 'VR')
            } elseif ($inVr -and $line -match '^\s*([A-Za-z0-9]+)\s*=\s*([^#;\r\n]+)') {
                $vrValues[$matches[1]] = $matches[2].Trim()
            }
        }
        # Resolve the final game launch arguments before reading INI defaults:
        # CONTROL and CORRECTNESS intentionally use different transport/cadence.
        # As in game settings parsing, the last repeated argument wins.
        $effectiveVrArguments = @{}
        foreach ($argument in $gameArgs) {
            if ($argument -match '^-([A-Za-z][A-Za-z0-9]*)=(.*)$') {
                $effectiveVrArguments[$matches[1]] = $matches[2]
            }
        }
        function Get-VrRuntimeValue([string]$key, [string]$fallback) {
            if ($effectiveVrArguments.ContainsKey($key)) {
                return [string]$effectiveVrArguments[$key]
            }
            if ($vrValues.ContainsKey($key)) { return [string]$vrValues[$key] }
            return $fallback
        }
        function Get-VrRuntimeBool([string]$key, [string]$fallback) {
            $value = (Get-VrRuntimeValue $key $fallback).Trim()
            return $(if ($value -in @('true','1','on','yes')) { '1' } else { '0' })
        }
        $prewarmEnvironment = [ordered]@{
            OUTRUN_VR_DIRECT_TRANSPORT = '1'
            OUTRUN_VR_DIRECT_ONLY = (Get-VrRuntimeBool 'DirectGpuOnly' 'true')
            OUTRUN_VR_DISABLE_DESKTOP_DUPLICATION = (Get-VrRuntimeBool 'DisableDesktopDuplication' 'false')
            OUTRUN_VR_TARGET_REFRESH_HZ = (Get-VrRuntimeValue 'TargetRefreshRateHz' '0')
            OUTRUN_VR_CADENCE_MODE = (Get-VrRuntimeValue 'FrameCadenceMode' '1')
            OUTRUN_VR_CADENCE_TARGET_HZ = (Get-VrRuntimeValue 'FrameCadenceTargetHz' '0')
            OUTRUN_VR_CADENCE_MAX_HZ = (Get-VrRuntimeValue 'FrameCadenceMaxHz' '120')
            OUTRUN_VR_CADENCE_TIMEOUT_MS = (Get-VrRuntimeValue 'FrameCadenceTimeoutMs' '35')
        }
        $savedPrewarmEnvironment = @{}
        try {
            foreach ($entry in $prewarmEnvironment.GetEnumerator()) {
                $savedPrewarmEnvironment[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, 'Process')
                [Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, 'Process')
            }
            $null = Start-Process -FilePath $xrHost -WorkingDirectory $root -WindowStyle Hidden -PassThru -ErrorAction Stop
            Write-Host 'OpenXR host prewarm launched asynchronously with matching VR policy.'
        } catch {
            Write-Warning "OpenXR prewarm unavailable: $($_.Exception.Message)"
        } finally {
            foreach ($entry in $prewarmEnvironment.GetEnumerator()) {
                [Environment]::SetEnvironmentVariable($entry.Key, $savedPrewarmEnvironment[$entry.Key], 'Process')
            }
        }
    }
}

# The OpenXR v3 shadow and a successful prewarm do not prove v2 host life.
# Never terminate the user's game merely because the host is missing.
$xrHostEverSeen=$false
$xrHostFailure=$false
$xrHostFailureReason=''
$xrHostMissingSince=$null
$xrHostRetryAttempted=$false
$xrHostRetryStartedAt=$null
$xrHostRetryError=''
$gameStartedAt=Get-Date
try{
    $p=Start-Process -FilePath $game -ArgumentList $gameArgs -WorkingDirectory $root -PassThru -ErrorAction Stop
    while(-not $p.HasExited){
        if($backend -eq 'd3d9'){
            $xrHostAlive=@(Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue).Count -gt 0
            if($xrHostAlive){$xrHostEverSeen=$true; $xrHostMissingSince=$null}
            else{
                if($null -eq $xrHostMissingSince){$xrHostMissingSince=Get-Date}
                # A user test observed a live game but no OpenXR host.
                # After sustained absence, request ONE bounded restart using
                # the same isolated VR policy as the initial prewarm.
                # Start-Process success never counts as a live XR session.
                $hostCheckNow=Get-Date
                if(-not $xrHostRetryAttempted -and
                   ($hostCheckNow-$gameStartedAt).TotalSeconds -ge 8 -and
                   ($hostCheckNow-$xrHostMissingSince).TotalSeconds -ge 6){
                    $xrHostRetryAttempted=$true
                    $xrHostRetryStartedAt=$hostCheckNow
                    if($xrHost -and $prewarmEnvironment -and
                       (Test-Path -LiteralPath $xrHost) -and
                       -not (Get-Process -Name 'outrun-vr-host' -ErrorAction SilentlyContinue)){
                        $retrySavedEnvironment=@{}
                        try {
                            foreach($entry in $prewarmEnvironment.GetEnumerator()){
                                $retrySavedEnvironment[$entry.Key]=[Environment]::GetEnvironmentVariable($entry.Key,'Process')
                                [Environment]::SetEnvironmentVariable($entry.Key,[string]$entry.Value,'Process')
                            }
                            $retryProcess=Start-Process -FilePath $xrHost -WorkingDirectory $root -WindowStyle Hidden -PassThru -ErrorAction Stop
                            Write-Warning "OpenXR host recovery requested once (PID=$($retryProcess.Id)); checking real process life."
                        } catch {
                            $xrHostRetryError=$_.Exception.Message
                            Write-Warning "OpenXR host recovery launch failed: $xrHostRetryError"
                        } finally {
                            foreach($entry in $prewarmEnvironment.GetEnumerator()){
                                [Environment]::SetEnvironmentVariable($entry.Key,$retrySavedEnvironment[$entry.Key],'Process')
                            }
                        }
                    } else {
                        $xrHostRetryError='No installed host/policy available for recovery'
                    }
                }
                # Keep the game running; permit ten seconds after a retry,
                # then report the original absence as a real failure. Never
                # retry a second time if this process also disappears.
                $hostGraceElapsed=if($xrHostRetryStartedAt){
                    ($hostCheckNow-$xrHostRetryStartedAt).TotalSeconds -ge 10
                } else {
                    ($hostCheckNow-$gameStartedAt).TotalSeconds -ge 15
                }
                if($hostGraceElapsed -and
                   ($hostCheckNow-$xrHostMissingSince).TotalSeconds -ge 10){
                    $xrHostFailure=$true
                    $xrHostFailureReason=if($xrHostEverSeen){'HOST_DISAPPEARED_DURING_GAME'}else{'HOST_NEVER_STARTED'}
                    Write-Warning "DX9Ex OpenXR host missing ($xrHostFailureReason). Leave game running until normal exit to collect logs."
                    break
                }
            }
        }
        Start-Sleep -Seconds 2
    }
    $p.WaitForExit()
    # A live OpenXR host does not mean the original game exited normally.
    $gameExitCode=$p.ExitCode
    if($backend -eq 'd3d9'){
        if(-not $xrHostEverSeen -and -not $xrHostFailure){
            $xrHostFailure=$true
            $xrHostFailureReason='GAME_EXITED_WITHOUT_HOST'
        }
        @(
          "sourceSha=$sourceSha",
          "gamePid=$($p.Id)",
          "gameExitCode=$gameExitCode",
          "hostProcessEverSeen=$xrHostEverSeen",
          "hostRecoveryAttempted=$xrHostRetryAttempted",
          "hostRecoveryLaunchError=$xrHostRetryError",
          "status=$(if($xrHostFailure){$xrHostFailureReason}elseif($gameExitCode -ne 0){'GAME_NONZERO_EXIT'}else{'PROCESS_OBSERVED_NOT_HMD_VERIFIED'})",
          "runtimeValidation=UNTESTED"
        ) | Set-Content -LiteralPath (Join-Path $sessionRoot 'DX9EX_LAUNCH_HEALTH.txt') -Encoding UTF8
        if($xrHostFailure){
            @(
              'DX9Ex OpenXR host missing during game.',
              "reason=$xrHostFailureReason",
              "hostRecoveryAttempted=$xrHostRetryAttempted",
              "hostRecoveryLaunchError=$xrHostRetryError",
              "gamePid=$($p.Id)",
              "session=$sessionRoot",
              'Check Virtual Desktop/VDXR OpenXR runtime and host log.',
              'A missing process does not establish the underlying runtime cause.'
            ) | Set-Content -LiteralPath (Join-Path $root 'OUTRUNVR_LAUNCH_ERROR.txt') -Encoding UTF8
        }
    }
    if($gameExitCode -ne 0 -and -not $xrHostFailure){
        # Write before the collector archives the failed session.
        @(
          'OutRun 2006 native game exited with a nonzero status.',
          "gameExitCode=$gameExitCode",
          "gamePid=$($p.Id)",
          "session=$sessionRoot",
          'An observed OpenXR host is not proof of game success.'
        ) | Set-Content -LiteralPath (Join-Path $root 'OUTRUNVR_LAUNCH_ERROR.txt') -Encoding UTF8
        Write-Warning "Game exited with $gameExitCode; collecting failure logs."
    }
    if($backend -eq 'd3d9' -and ($xrHostFailure -or $gameExitCode -ne 0)){
        # The collector archives the session directory, not arbitrary root
        # text files. Preserve the visible root error and put its identical
        # bytes in the session ZIP for host-loss and native-game crashes.
        Copy-Item -LiteralPath (Join-Path $root 'OUTRUNVR_LAUNCH_ERROR.txt') -Destination (Join-Path $sessionRoot 'OUTRUNVR_LAUNCH_ERROR.txt') -Force
    }
} finally {
    # Stop only the sampler started by this run, never a user's other nvidia-smi.
    if ($gpuCaptureRequested) {
        $samplerExitedEarly = $false
        if ($gpuSampler) {
            try {
                $samplerExitedEarly = $gpuSampler.HasExited
                if (-not $samplerExitedEarly) {
                    Stop-Process -Id $gpuSampler.Id -ErrorAction Stop
                    [void]$gpuSampler.WaitForExit(5000)
                }
            } catch {
                $gpuCaptureStatus = 'STOP_FAILED'
                Write-Warning "GPU sampler shutdown failed: $($_.Exception.Message)"
            } finally {
                $gpuSampler.Dispose()
            }
        }
        $gpuSampleCount = 0
        if (Test-Path -LiteralPath $gpuCsv) {
            # nvidia-smi emits one header followed by sampled data rows.
            $gpuLines = @(Get-Content -LiteralPath $gpuCsv -ErrorAction SilentlyContinue)
            $gpuSampleCount = @($gpuLines | Where-Object {
                $_ -and $_ -notmatch '^\s*timestamp\s*,'
            }).Count
        }
        if ($gpuCaptureStatus -eq 'SAMPLING') {
            if ($samplerExitedEarly) {
                $gpuCaptureStatus = 'SAMPLER_EXITED_EARLY'
            } elseif ($gpuSampleCount -gt 0) {
                $gpuCaptureStatus = 'CAPTURED'
            } else {
                $gpuCaptureStatus = 'NO_SAMPLES'
            }
        }
        [ordered]@{
            SchemaVersion = 1
            Status = $gpuCaptureStatus
            SessionId = [string]$state.SessionId
            StartedUtc = $gpuCaptureStartedUtc
            FinishedUtc = (Get-Date).ToUniversalTime().ToString('o')
            SamplingSeconds = 1
            SampleCount = $gpuSampleCount
            CsvName = if ($gpuSampleCount -gt 0) { 'outrun-vr-gpu-utilization.csv' } else { $null }
            Scope = 'WHOLE_NVIDIA_GPU_INCLUDING_GAME_HOST_COMPOSITOR_ENCODER'
            GPUFrameTimeMeasured = $false
            D3D9TimestampQueryRequested = $gpuDiagnosticActive
            D3D9TimestampLogMarker = if ($gpuDiagnosticActive) { 'VR GPU WATER 5s' } else { $null }
            HmdRuntimeVerified = $false
        } | ConvertTo-Json -Depth 3 |
            Set-Content (Join-Path $sessionRoot 'gpu-utilization-status.json') -Encoding UTF8
    }
    $env:OUTRUN_VR_GPU_SCENE=$oldGpuScene
    $env:OUTRUN_VR_GPU_PROFILE=$oldGpuProfiling
    $env:OUTRUN_VR_PACING_DIAGNOSTICS=$oldPacingDiagnostics
    $env:OUTRUN_VR_FORCE_DISABLED=$oldVrForceDisabled
    $env:OUTRUN_VR_TEST_PROFILE=$oldTestProfile
    $env:OUTRUN_VR_PERFORMANCE_PROFILE=$oldPerformanceProfile
    $env:OUTRUN_VR_R30_PARTICLE_VB=$oldParticleGpuUpload
    $env:OUTRUN_VR_SHADER_FINGERPRINT=$oldShaderFingerprint
    $env:OUTRUN_VR_EXE_SEMANTICS_VERIFIED=$oldExeSemanticsVerified
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
    Write-Warning 'outrun-vr-host.exe is still running. Close it, then run: powershell -NoProfile -ExecutionPolicy Bypass -File .\Collect-OutRunVRLogs.ps1 . No logs were deleted.'
    exit 2
}

& $collector
if (-not $?) { throw 'VR log collector failed after game exit.' }
if($xrHostFailure){
    Write-Warning 'OpenXR host failure: see OUTRUNVR_LAUNCH_ERROR.txt and DX9EX_LAUNCH_HEALTH.txt in session logs.'
    try {
       Add-Type -AssemblyName System.Windows.Forms
       [void][System.Windows.Forms.MessageBox]::Show('OpenXR host missing. See OUTRUNVR_LAUNCH_ERROR.txt; logs were collected.','DX9Ex VR launch failure')
    } catch {}
    exit 5
}
if($gameExitCode -ne 0){
    # Windows exception NTSTATUS may be signed negative. Use a POSITIVE
    # errorlevel, so the visible CMD 'if errorlevel 1' never reports OK.
    Write-Warning "OutRun game exit ${gameExitCode}: DX9Ex test FAILED (logs collected)."
    exit 7
}
