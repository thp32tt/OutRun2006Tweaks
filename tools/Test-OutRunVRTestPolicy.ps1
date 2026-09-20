$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
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
    Assert-True ($profile.Name -in @('CONTROL','CORRECTNESS','PERFORMANCE')) "invalid profile identity"
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
Assert-True ($text['OutRunVR-Backend-Selector.ps1'] -match 'CORRECTNESS') 'GUI must expose CORRECTNESS'
Assert-True ($text['OutRunVR-Backend-Selector.ps1'] -match 'CONTROL') 'GUI must expose CONTROL'
Assert-True ($text['OutRunVR-Backend-Selector.ps1'] -match 'PERFORMANCE') 'GUI must expose PERFORMANCE'

$statePath = Join-Path (Split-Path -Parent $root) 'docs/VR_AUTODEV_STATE.json'
Assert-True (Test-Path $statePath) 'VR_AUTODEV_STATE.json missing'
$state = Get-Content $statePath -Raw | ConvertFrom-Json
Assert-True ($state.schemaVersion -ge 2) 'autodev state schema must include runtime-test policy'
Assert-True ($null -ne $state.runtimeTestQueue) 'runtimeTestQueue missing'
Assert-True ($null -ne $state.eveningCandidate) 'eveningCandidate state missing'
Assert-True ($state.testProfiles.CORRECTNESS.defaultUserTest -eq $true) 'CORRECTNESS must be the default user runtime test'
Assert-True ($state.testProfiles.CONTROL.defaultUserTest -eq $false) 'CONTROL must be optional'
Assert-True ($state.testProfiles.PERFORMANCE.defaultUserTest -eq $false) 'PERFORMANCE must be optional'

Write-Host 'VR test policy verification passed: profile identity, runtime defaults, session/log separation, GUI exposure and TEST_LEVEL state are consistent.'
