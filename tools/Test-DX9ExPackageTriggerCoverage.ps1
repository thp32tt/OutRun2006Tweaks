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
    Require ($workflow.Contains($needle)) "DX9Ex active workflow trigger missing packaged/runtime path: $Path"
}

# All tool files copied by the active package loop must also select this workflow
# when they change. Parse the literal package inventory so the verifier fails if
# a new packaged tool is added without a matching push-path trigger.
$copyLoopPattern = "(?s)foreach \(\$file in @\((?<items>.*?)\)\) \{\s*Copy-Item \(Join-Path 'tools' \$file\)"
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

# Repo files copied directly into the tester package.
foreach ($path in @(
    "OutRun2006Tweaks.ini",
    "OutRun2006Tweaks.lods.ini",
    "docs/VR_TEST_STRATEGY.md"
)) {
    Require-TriggerPath $path
}

# Runtime-consumed analyzer: the runner/collector can use its output even though
# it is not one of the PowerShell launcher files in the copy loop.
Require-TriggerPath "tools/analyze_outrun_assets.py"

# Changes to this verifier must validate themselves.
Require-TriggerPath "tools/Test-DX9ExPackageTriggerCoverage.ps1"

Write-Host ("DX9Ex package trigger coverage passed. packagedTools={0}" -f $toolNames.Count)
