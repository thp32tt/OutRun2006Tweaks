$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $root
. (Join-Path $root 'OutRunVR-TestProfiles.ps1')

function Assert-True([bool]$condition,[string]$message) {
    if (-not $condition) { throw $message }
}

function Has-Argument($profile,[string]$argument) {
    return @($profile.Arguments) -contains $argument
}

$control = Get-OutRunVRTestProfile -Name CONTROL
$correctness = Get-OutRunVRTestProfile -Name CORRECTNESS
$performance = Get-OutRunVRTestProfile -Name PERFORMANCE

# A FastLoad value above zero is not safe for the current VR recovery-baseline
# startup path. 2026-09-23 Quest/VDXR evidence showed every FastLoad=3 profile
# remained in the white loading loop with authoritativeSeed=0/stereoAllowed=0,
# while HUD_MENU (FastLoad=0) progressed to a verified c64 baseline/gameplay.
$allRuntimeProfileNames = @(
    'CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE',
    'STAGE_DIAGNOSTIC','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512'
)
foreach($profileName in $allRuntimeProfileNames) {
    $runtimeProfile = Get-OutRunVRTestProfile -Name $profileName
    Assert-True (Has-Argument $runtimeProfile '-FramerateFastLoad=0') "${profileName}: VR runtime profiles must keep FastLoad disabled to prevent startup white-screen recovery deadlock"
}

foreach($profile in @($control,$correctness,$performance)) {
    Assert-True ($profile.Name -in @('CONTROL','CORRECTNESS','PERFORMANCE')) 'invalid profile identity'
    Assert-True (Has-Argument $profile '-PreferD3D9Ex=true') "$($profile.Name): D3D9Ex reference must be preferred"
    Assert-True (Has-Argument $profile '-DisableDesktopDuplication=false') "$($profile.Name): fallback must remain available by default"
    Assert-True (Has-Argument $profile '-TargetRefreshRateHz=0') "$($profile.Name): refresh must follow OpenXR/VDXR"
    Assert-True (Has-Argument $profile '-SkyGlowFactor=1') "$($profile.Name): test policy requires SkyGlowFactor=1"
    Assert-True ($profile.Environment.OUTRUN_VR_TEST_PROFILE -eq $profile.Name) "$($profile.Name): environment identity mismatch"
}

Assert-True (Has-Argument $control '-DirectGpuOnly=false') 'CONTROL must keep DirectGPU optional for A/B isolation'
Assert-True (Has-Argument $performance '-DirectGpuOnly=false') 'PERFORMANCE must keep fallback transport available for explicit performance comparison'
Assert-True (Has-Argument $correctness '-DirectGpuOnly=true') 'CORRECTNESS must use the runtime-proven DirectGPU visual owner'
Assert-True (Has-Argument $correctness '-CullingUnionFov=false') 'CORRECTNESS must keep union-FOV projection mutation disabled'
Assert-True (Has-Argument $control '-FramerateLimit=60') 'CONTROL must remain conservative 60 Hz comparison'
Assert-True ($control.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -eq '0') 'CONTROL must not enable performance experiments'
Assert-True ($correctness.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -eq '0') 'CORRECTNESS must keep performance experiments isolated'
Assert-True (Has-Argument $correctness '-FramerateLimit=60') 'CORRECTNESS must remain a conservative 60 Hz isolation baseline'
Assert-True (Has-Argument $correctness '-FramerateFastLoad=0') 'CORRECTNESS must disable FastLoad'
Assert-True (Has-Argument $correctness '-FramerateInterpolation=false') 'CORRECTNESS must disable interpolation'
Assert-True (Has-Argument $correctness '-FramerateUnlockExperimental=false') 'CORRECTNESS must disable experimental framerate unlock'
Assert-True (Has-Argument $correctness '-FrameCadenceMode=0') 'CORRECTNESS must disable phase-lock cadence'
Assert-True (Has-Argument $correctness '-DisableDesktopVsync=false') 'CORRECTNESS must preserve desktop VSync'
Assert-True ($performance.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -eq '1') 'PERFORMANCE must explicitly opt into performance experiments'
Assert-True (Has-Argument $correctness '-FrameCadenceTargetHz=0') 'CORRECTNESS must use runtime-selected cadence'
Assert-True (Has-Argument $performance '-FrameCadenceTargetHz=0') 'PERFORMANCE must use runtime-selected cadence'

$requiredFiles = @(
    'Select-OutRunVRBackend.ps1',
    'Run-OutRunVRTest.ps1',
    'Collect-OutRunVRLogs.ps1',
    'OutRunVR-Test-Selector.ps1'
)
$text = @{}
$parseTargets = @('OutRunVR-TestProfiles.ps1') + $requiredFiles
foreach($name in $parseTargets) {
    $p = Join-Path $root $name
    Assert-True (Test-Path $p) "missing test tool: $name"
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$errors)
    Assert-True ($errors.Count -eq 0) ("PowerShell parse failure in {0}: {1}" -f $name, (($errors | ForEach-Object {$_.Message}) -join '; '))
    if($name -in $requiredFiles){ $text[$name] = Get-Content $p -Raw }
}

Assert-True ($text['Select-OutRunVRBackend.ps1'] -match 'TestProfile') 'selector must persist TestProfile'
Assert-True ($text['Run-OutRunVRTest.ps1'] -match 'Get-OutRunVRTestProfile') 'runner must consume profile definitions'
Assert-True ($text['Collect-OutRunVRLogs.ps1'] -match 'TEST_PROFILE') 'collector manifest must record profile'
Assert-True ($text['Collect-OutRunVRLogs.ps1'] -match '\$variant/\$profile/\$session') 'collector path must separate Variant/Profile/Session'
Assert-True ($text['Collect-OutRunVRLogs.ps1'] -match 'captureRoot') 'collector must include capture bundles'
$r56Variants=@(
    'R56_01_ZERO',
    'R56_02_SCALE35',
    'R56_03_WORLD35',
    'R56_04_RANKZERO',
    'R56_05_POSITION_XP96',
    'R56_06_POSITION_XM96',
    'R56_07_POSITION_XS35',
    'R56_08_POSITION_XCENTER',
    'R56_09_RANK13_XP96',
    'R56_10_RANK13_XM96',
    'R56_11_RANK13_YM72',
    'R56_12_RANK13_CENTER',
    'R56_13_RANK46_XP96',
    'R56_14_RANK46_YM72',
    'R56_15_RANK46_CENTER',
    'R56_16_RANK13_AS_HUD',
    'R56_17_RANK46_AS_HUD',
    'R56_18_RANK46_NEXTDRAW',
    'R56_19_POSITION_NEXTDRAW',
    'R56_20_ALLSCREEN_RAW'
)
foreach($id in $r56Variants){
    Assert-True ($text['OutRunVR-Test-Selector.ps1'] -match [regex]::Escape($id)) "single GUI must expose $id"
    Assert-True ($text['Run-OutRunVRTest.ps1'] -match [regex]::Escape($id)) "runner must map $id"
}
Assert-True ($text['Run-OutRunVRTest.ps1'] -match 'OUTRUN_VR_HUD_PROBE') 'runner must set the R56 runtime probe selector'
Assert-True (-not (Test-Path (Join-Path $root 'OutRunVR-Backend-Selector.ps1'))) 'obsolete backend GUI selector must stay removed'
Assert-True (-not (Test-Path (Join-Path $root 'OutRunVR-Slot-Selector.ps1'))) 'obsolete slot GUI selector must stay removed'

$watchdogPath = Join-Path $repoRoot 'vrhost/src/diagnostics/runtime_watchdog.cpp'
Assert-True (Test-Path $watchdogPath) 'runtime watchdog source missing'
$watchdog = Get-Content $watchdogPath -Raw
Assert-True ($watchdog -match 'VK_F9') 'diagnostic capture must use the non-conflicting F9 trigger'
Assert-True ($watchdog -match 'VK_CONTROL') 'diagnostic capture must require Ctrl modifier'
Assert-True ($watchdog -match 'RollingSampleCount\s*=\s*100') 'rolling capture must remain bounded near 10 seconds at 100 ms sampling'
Assert-True ($watchdog -match 'std::ios::app') 'watchdog log must preserve same-session host restarts'

$activeWorkflowPath = Join-Path $repoRoot '.github/workflows/vr-dx9ex-active.yml'
$comparisonWorkflowPath = Join-Path $repoRoot '.github/workflows/vr-unified-backends.yml'
Assert-True (Test-Path $activeWorkflowPath) 'single active DX9Ex workflow missing'
Assert-True (Test-Path $comparisonWorkflowPath) 'manual comparison workflow missing'
$activeWorkflow = Get-Content $activeWorkflowPath -Raw
$comparisonWorkflow = Get-Content $comparisonWorkflowPath -Raw
Assert-True ($activeWorkflow -match 'name:\s*DX9Ex Active Validation') 'active workflow identity mismatch'
Assert-True ($activeWorkflow -notmatch '(?m)^\s*matrix:\s*$') 'routine active workflow must not build a variant matrix'
Assert-True ($activeWorkflow -notmatch 'P1_C1_FAST_WORLD|P2_C2_FAST_HUD|P4_R26_HUD_SAFE') 'routine active workflow leaked comparison variants'
Assert-True ($comparisonWorkflow -match 'name:\s*DX9Ex Comparison Matrix \(Manual\)') 'comparison workflow identity mismatch'
Assert-True ($comparisonWorkflow -notmatch '(?m)^\s*push:\s*$') 'four-way comparison workflow must remain manual-only'

$statePath = Join-Path $repoRoot 'docs/VR_AUTODEV_STATE.json'
Assert-True (Test-Path $statePath) 'VR_AUTODEV_STATE.json missing'
$state = Get-Content $statePath -Raw | ConvertFrom-Json
Assert-True ($state.schemaVersion -ge 2) 'autodev state schema must include runtime-test policy'
Assert-True ($null -ne $state.runtimeTestQueue) 'runtimeTestQueue missing'
Assert-True ($null -ne $state.eveningCandidate) 'eveningCandidate state missing'
Assert-True ($state.testProfiles.CORRECTNESS.defaultUserTest -eq $true) 'CORRECTNESS must be the default user runtime test'
Assert-True ($state.testProfiles.CONTROL.defaultUserTest -eq $false) 'CONTROL must be optional'
Assert-True ($state.testProfiles.PERFORMANCE.defaultUserTest -eq $false) 'PERFORMANCE must be optional'

Write-Host 'VR test policy verification passed: profile identity, runtime defaults, session/log separation, single user-facing semantic selector, bounded Ctrl+F9 capture, single-active CI and TEST_LEVEL state are consistent.'
