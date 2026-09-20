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

foreach($profile in @($control,$correctness,$performance)) {
    Assert-True ($profile.Name -in @('CONTROL','CORRECTNESS','PERFORMANCE')) 'invalid profile identity'
    Assert-True (Has-Argument $profile '-PreferD3D9Ex=true') "$($profile.Name): D3D9Ex reference must be preferred"
    Assert-True (Has-Argument $profile '-DirectGpuOnly=false') "$($profile.Name): DirectGPU must remain optional by default"
    Assert-True (Has-Argument $profile '-DisableDesktopDuplication=false') "$($profile.Name): fallback must remain available by default"
    Assert-True (Has-Argument $profile '-TargetRefreshRateHz=0') "$($profile.Name): refresh must follow OpenXR/VDXR"
    Assert-True (Has-Argument $profile '-SkyGlowFactor=1') "$($profile.Name): test policy requires SkyGlowFactor=1"
    Assert-True ($profile.Environment.OUTRUN_VR_TEST_PROFILE -eq $profile.Name) "$($profile.Name): environment identity mismatch"
}

Assert-True (Has-Argument $control '-FramerateLimit=60') 'CONTROL must remain conservative 60 Hz comparison'
Assert-True ($control.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -eq '0') 'CONTROL must not enable performance experiments'
Assert-True ($correctness.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -eq '0') 'CORRECTNESS must keep performance experiments isolated'
Assert-True ($performance.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -eq '1') 'PERFORMANCE must explicitly opt into performance experiments'
Assert-True (Has-Argument $correctness '-FrameCadenceTargetHz=0') 'CORRECTNESS must use runtime-selected cadence'
Assert-True (Has-Argument $performance '-FrameCadenceTargetHz=0') 'PERFORMANCE must use runtime-selected cadence'

$requiredFiles = @(
    'Select-OutRunVRBackend.ps1',
    'Run-OutRunVRTest.ps1',
    'Collect-OutRunVRLogs.ps1',
    'OutRunVR-Backend-Selector.ps1'
)
$text = @{}
foreach($name in $requiredFiles) {
    $p = Join-Path $root $name
    Assert-True (Test-Path $p) "missing test tool: $name"
    $text[$name] = Get-Content $p -Raw
}

Assert-True ($text['Select-OutRunVRBackend.ps1'] -match 'TestProfile') 'selector must persist TestProfile'
Assert-True ($text['Run-OutRunVRTest.ps1'] -match 'Get-OutRunVRTestProfile') 'runner must consume profile definitions'
Assert-True ($text['Collect-OutRunVRLogs.ps1'] -match 'TEST_PROFILE') 'collector manifest must record profile'
Assert-True ($text['Collect-OutRunVRLogs.ps1'] -match '\$variant/\$profile/\$session') 'collector path must separate Variant/Profile/Session'
Assert-True ($text['Collect-OutRunVRLogs.ps1'] -match 'captureRoot') 'collector must include capture bundles'
Assert-True ($text['OutRunVR-Backend-Selector.ps1'] -match 'CORRECTNESS') 'GUI must expose CORRECTNESS'
Assert-True ($text['OutRunVR-Backend-Selector.ps1'] -match 'CONTROL') 'GUI must expose CONTROL'
Assert-True ($text['OutRunVR-Backend-Selector.ps1'] -match 'PERFORMANCE') 'GUI must expose PERFORMANCE'

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

Write-Host 'VR test policy verification passed: profile identity, runtime defaults, session/log separation, GUI exposure, bounded Ctrl+F9 capture, single-active CI and TEST_LEVEL state are consistent.'
