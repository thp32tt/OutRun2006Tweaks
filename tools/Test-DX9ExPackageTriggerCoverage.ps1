param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$workflowPath = Join-Path $RepoRoot ".github/workflows/vr-dx9ex-active.yml"
Require (Test-Path $workflowPath) "Missing DX9Ex active workflow"
$workflow = Get-Content -Raw $workflowPath

function Require-TriggerPath([string]$Path) {
    $needle = "- '$Path'"
    Require ($workflow.Contains($needle)) "DX9Ex active trigger missing dependency: $Path"
}

foreach ($path in @(
    "tools/Test-OutRunVRTestPolicy.ps1",
    "tools/Test-VRRegressionKnowledge.ps1",
    "tools/verify_vr_architecture.py",
    "tools/verify_vr_r32_review.py",
    "tools/Test-DX9ExPackageTriggerCoverage.ps1"
)) {
    Require-TriggerPath $path
}

$copyLoopPattern = '(?s)foreach \(\$file in @\((?<items>.*?)\)\) \{\s*Copy-Item \(Join-Path ''tools'' \$file\)'
$copyLoop = [regex]::Match($workflow, $copyLoopPattern)
Require $copyLoop.Success "Could not locate active package tool-copy inventory"

$toolNames = @(
    [regex]::Matches($copyLoop.Groups["items"].Value, "'([^']+)'") |
        ForEach-Object { $_.Groups[1].Value }
)
Require ($toolNames.Count -gt 0) "Active package tool-copy inventory is empty"

foreach ($tool in $toolNames) {
    Require-TriggerPath ("tools/" + $tool)
}

foreach ($path in @(
    "OutRun2006Tweaks.ini",
    "OutRun2006Tweaks.lods.ini",
    "docs/VR_TEST_STRATEGY.md",
    "tools/analyze_outrun_assets.py"
)) {
    Require-TriggerPath $path
}

Require ($workflow.Contains('Copy-Item tools/analyze_outrun_assets.py (Join-Path $dir ''analyze_outrun_assets.py'')')) "Asset analyzer is not copied into the active tester package"
Require ($workflow.Contains('''OutRunVR-TestProfiles.ps1'',''analyze_outrun_assets.py'',''BUILD_INPUTS.json''')) "Asset analyzer is not required by active package validation"

Write-Host ("DX9Ex dependency closure passed. packagedTools={0}" -f $toolNames.Count)
