Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$runnerSource = Join-Path $PSScriptRoot 'Run-OutRunVRTest.ps1'
$collectorSource = Join-Path $PSScriptRoot 'Collect-OutRunVRLogs.ps1'
foreach($path in @($runnerSource,$collectorSource)){
    if(!(Test-Path $path -PathType Leaf)){throw "Missing failure-diagnostic dependency: $path"}
}

$runnerText = Get-Content $runnerSource -Raw
foreach($required in @(
    "GAME_LAUNCH_OR_WAIT",
    "HOST_TEARDOWN",
    '& $collector -Emergency',
    "RUNNER_FAILURE.json"
)){
    if($runnerText -notmatch [regex]::Escape($required)){
        throw "Runner diagnostic survivability contract missing: $required"
    }
}

$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('outrun-runner-failure-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $testRoot | Out-Null

try{
    # Behavior-test F31 with a deliberately invalid game executable. The real
    # runner must collect the prepared session before rethrowing Start-Process.
    Copy-Item $runnerSource (Join-Path $testRoot 'Run-OutRunVRTest.ps1') -Force
    Set-Content (Join-Path $testRoot 'Select-OutRunVRBackend.ps1') '# test stub' -Encoding UTF8
    @'
param([switch]$All,[switch]$Emergency)
Set-Content (Join-Path $PSScriptRoot 'COLLECTOR_CALLED.txt') ("emergency=" + [bool]$Emergency) -Encoding ascii
if(Test-Path (Join-Path $PSScriptRoot 'FORCE_COLLECTOR_FAILURE.txt')){
    throw 'simulated collector failure'
}
'@ | Set-Content (Join-Path $testRoot 'Collect-OutRunVRLogs.ps1') -Encoding UTF8
    @'
function Get-OutRunVRTestProfile {
    param([string]$Name)
    return [ordered]@{
        Arguments=@()
        Environment=[ordered]@{
            OUTRUN_VR_TEST_PROFILE=$Name
            OUTRUN_VR_PERFORMANCE_PROFILE='0'
        }
    }
}
'@ | Set-Content (Join-Path $testRoot 'OutRunVR-TestProfiles.ps1') -Encoding UTF8

    Set-Content (Join-Path $testRoot 'OR2006C2C.EXE') 'not-a-valid-win32-image' -Encoding ascii -NoNewline
    Set-Content (Join-Path $testRoot 'ACTIVE_VR_BACKEND.txt') @(
        'backend=dxvk-safe'
        'variant=E_DXVK_SAFE'
        'profile=CORRECTNESS'
        'sourceSha=test-source'
        'matrix=TEST_MATRIX'
        'session=launch-failure'
    ) -Encoding ascii

    $launchStarted=(Get-Date).ToUniversalTime().AddMinutes(-1).ToString('o')
    [ordered]@{
        SchemaVersion=4
        BuildMatrixId='TEST_MATRIX'
        VariantId='E_DXVK_SAFE'
        Backend='dxvk-safe'
        TestProfile='CORRECTNESS'
        SourceSha='test-source'
        SessionId='launch-failure'
        StartedUtc=$launchStarted
        ConfigSha256='missing'
    } | ConvertTo-Json | Set-Content (Join-Path $testRoot 'CURRENT_VR_SESSION.json') -Encoding UTF8

    $launchFailed=$false
    try{
        & (Join-Path $testRoot 'Run-OutRunVRTest.ps1') -TestProfile CORRECTNESS
    }catch{
        $launchFailed=$true
    }
    if(-not $launchFailed){throw 'F31 behavior test expected invalid executable launch failure.'}
    if(!(Test-Path (Join-Path $testRoot 'COLLECTOR_CALLED.txt'))){
        throw 'F31 launch failure bypassed collector.'
    }
    $launchFailureJson = Join-Path $testRoot 'logs/TEST_MATRIX/E_DXVK_SAFE/CORRECTNESS/launch-failure/RUNNER_FAILURE.json'
    if(!(Test-Path $launchFailureJson -PathType Leaf)){throw 'F31 RUNNER_FAILURE.json missing.'}
    $launchFailure=Get-Content $launchFailureJson -Raw | ConvertFrom-Json
    if([string]$launchFailure.Phase -ne 'GAME_LAUNCH_OR_WAIT'){
        throw "F31 failure phase mismatch: $($launchFailure.Phase)"
    }

    # Behavior-test F33 result precedence: if collection itself throws after a
    # launch failure, the original runner failure must remain the propagated
    # result while the collector failure is recorded separately.
    Remove-Item (Join-Path $testRoot 'COLLECTOR_CALLED.txt') -Force -ErrorAction SilentlyContinue
    Set-Content (Join-Path $testRoot 'FORCE_COLLECTOR_FAILURE.txt') '1' -Encoding ascii
    $f33State=[ordered]@{
        SchemaVersion=4
        BuildMatrixId='TEST_MATRIX'
        VariantId='E_DXVK_SAFE'
        Backend='dxvk-safe'
        TestProfile='CORRECTNESS'
        SourceSha='test-source'
        SessionId='collector-precedence'
        StartedUtc=(Get-Date).ToUniversalTime().AddMinutes(-1).ToString('o')
        ConfigSha256='missing'
    }
    $f33State | ConvertTo-Json | Set-Content (Join-Path $testRoot 'CURRENT_VR_SESSION.json') -Encoding UTF8
    $f33Error=$null
    try{
        & (Join-Path $testRoot 'Run-OutRunVRTest.ps1') -TestProfile CORRECTNESS
    }catch{
        $f33Error=$_.Exception
    }
    if(!$f33Error){throw 'F33 behavior test expected the original launch failure to propagate.'}
    if($f33Error.Message -match 'simulated collector failure'){
        throw 'F33 collector failure obscured the original launch failure.'
    }
    if(!(Test-Path (Join-Path $testRoot 'COLLECTOR_CALLED.txt'))){
        throw 'F33 collector was not attempted after the launch failure.'
    }
    $f33Root=Join-Path $testRoot 'logs/TEST_MATRIX/E_DXVK_SAFE/CORRECTNESS/collector-precedence'
    $f33Runner=Get-Content (Join-Path $f33Root 'RUNNER_FAILURE.json') -Raw|ConvertFrom-Json
    if([string]$f33Runner.Phase -ne 'GAME_LAUNCH_OR_WAIT'){
        throw "F33 original runner failure was not preserved: $($f33Runner.Phase)"
    }
    $f33Collector=Get-Content (Join-Path $f33Root 'COLLECTOR_FAILURE.json') -Raw|ConvertFrom-Json
    if([string]$f33Collector.Phase -ne 'DIAGNOSTIC_COLLECTION'){
        throw "F33 collector phase mismatch: $($f33Collector.Phase)"
    }
    if([string]$f33Collector.PrimaryFailure -ne 'GAME_LAUNCH_OR_WAIT'){
        throw "F33 collector primary-failure binding mismatch: $($f33Collector.PrimaryFailure)"
    }
    Remove-Item (Join-Path $testRoot 'FORCE_COLLECTOR_FAILURE.txt') -Force

    $gameResultIndex=$runnerText.IndexOf('if($gameExitCode -ne 0){')
    $collectorFailureIndex=$runnerText.LastIndexOf('if($collectorFailure){throw $collectorFailure}')
    $collectorExitIndex=$runnerText.LastIndexOf('if($collectorExitCode -ne 0){exit $collectorExitCode}')
    if($gameResultIndex -lt 0 -or $collectorFailureIndex -le $gameResultIndex -or $collectorExitIndex -le $gameResultIndex){
        throw 'F33 source-order contract does not preserve game result ahead of collector failure.'
    }

    # Behavior-test emergency collector semantics used by F32. It must create a
    # diagnostic archive without consuming source evidence or rotating session.
    $emergencyRoot = Join-Path $testRoot 'emergency'
    New-Item -ItemType Directory -Force $emergencyRoot | Out-Null
    Copy-Item $collectorSource (Join-Path $emergencyRoot 'Collect-OutRunVRLogs.ps1') -Force
    $started=(Get-Date).ToUniversalTime().AddMinutes(-1)
    Set-Content (Join-Path $emergencyRoot 'ACTIVE_VR_BACKEND.txt') @(
        'backend=dxvk-safe'
        'variant=E_DXVK_SAFE'
        'profile=CORRECTNESS'
        'sourceSha=test-source'
        'matrix=TEST_MATRIX'
        'session=emergency-session'
        ("startedUtc=" + $started.ToString('o'))
    ) -Encoding ascii
    $state=[ordered]@{
        SchemaVersion=4
        BuildMatrixId='TEST_MATRIX'
        VariantId='E_DXVK_SAFE'
        Backend='dxvk-safe'
        TestProfile='CORRECTNESS'
        SourceSha='test-source'
        SessionId='emergency-session'
        StartedUtc=$started.ToString('o')
        ConfigSha256='missing'
    }
    $stateJson=$state|ConvertTo-Json
    $stateJson|Set-Content (Join-Path $emergencyRoot 'CURRENT_VR_SESSION.json') -Encoding UTF8
    Set-Content (Join-Path $emergencyRoot 'OutRun2006Tweaks-test.log') 'emergency evidence' -Encoding ascii

    & (Join-Path $emergencyRoot 'Collect-OutRunVRLogs.ps1') -Emergency
    if(!(Test-Path (Join-Path $emergencyRoot 'OutRun2006Tweaks-test.log'))){
        throw 'F32 emergency collector consumed source log evidence.'
    }
    $stateAfter=Get-Content (Join-Path $emergencyRoot 'CURRENT_VR_SESSION.json') -Raw|ConvertFrom-Json
    if([string]$stateAfter.SessionId -ne 'emergency-session'){
        throw 'F32 emergency collector rotated CURRENT_VR_SESSION.json.'
    }
    $manifestPath=Join-Path $emergencyRoot 'logs/TEST_MATRIX/E_DXVK_SAFE/CORRECTNESS/emergency-session/variant_manifest.json'
    if(!(Test-Path $manifestPath -PathType Leaf)){throw 'F32 emergency variant_manifest.json missing.'}
    $manifest=Get-Content $manifestPath -Raw|ConvertFrom-Json
    if(-not [bool]$manifest.EmergencySnapshot){throw 'F32 emergency manifest flag missing.'}
    if([string]$manifest.LogBoundary -ne 'emergency-snapshot-running-process'){
        throw "F32 emergency log boundary mismatch: $($manifest.LogBoundary)"
    }
    $zip=@(Get-ChildItem $emergencyRoot -Filter 'OutRun2_VR_ANALYZE_*.zip' -File)
    if($zip.Count -ne 1){throw "F32 emergency diagnostic archive count mismatch: $($zip.Count)"}

    Write-Host 'Runner launch/stuck-host/collector-failure diagnostic survivability PASS'
} finally {
    if(Test-Path $testRoot){
        Remove-Item $testRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
