param(
    [string]$GameExe = 'OR2006C2C.EXE',
    [ValidateSet('CONTROL','CORRECTNESS','PERFORMANCE')]
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

$patterns=@(
    'OutRun2006Tweaks*.log',
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
    & $selector -Backend $backend -TestProfile $TestProfile
    if($LASTEXITCODE -and $LASTEXITCODE -ne 0){throw 'Failed to seal stale logs before launch.'}
}

$state=Get-Content $current -Raw|ConvertFrom-Json
if($state.TestProfile -and $state.TestProfile -ne $TestProfile){
    & $selector -Backend $backend -TestProfile $TestProfile
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

$sessionRoot=Join-Path $root ("logs/{0}/{1}/{2}/{3}" -f $state.BuildMatrixId,$state.VariantId,$TestProfile,$state.SessionId)
New-Item -ItemType Directory -Force $sessionRoot|Out-Null
@(
    "backend=$backend"
    "profile=$TestProfile"
    "forceVrDisabled=$($backend -eq '2d')"
    "arguments=$($gameArgs -join ' ')"
)|Set-Content (Join-Path $sessionRoot 'RUN_OVERRIDES.txt') -Encoding UTF8
Write-Host "Runtime overrides: $($gameArgs -join ' ')"

$dxvkMode = $backend -eq 'dxvk-safe' -or $backend -eq 'dxvk'
$oldVkDisable = $env:VK_LOADER_LAYERS_DISABLE
$oldVkInstanceLayers = $env:VK_INSTANCE_LAYERS
$oldVkDebug = $env:VK_LOADER_DEBUG
$oldVrForceDisabled = $env:OUTRUN_VR_FORCE_DISABLED
$oldTestProfile = $env:OUTRUN_VR_TEST_PROFILE
$oldPerformanceProfile = $env:OUTRUN_VR_PERFORMANCE_PROFILE

if($backend -eq '2d'){
    $env:OUTRUN_VR_FORCE_DISABLED='1'
    Write-Host '2D control isolation: all OpenXR/VR hook installers are disabled for this process.'
}else{
    $env:OUTRUN_VR_FORCE_DISABLED=$null
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
