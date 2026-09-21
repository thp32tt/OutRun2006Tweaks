param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$registryPath = Join-Path $RepoRoot "docs/VR_REGRESSION_KNOWLEDGE.json"
$historyPath = Join-Path $RepoRoot "docs/VR_PROBLEM_HISTORY.md"

Require (Test-Path $registryPath) "Missing regression registry"
Require (Test-Path $historyPath) "Missing human-readable problem history"

try {
    $registry = Get-Content -Raw $registryPath | ConvertFrom-Json -Depth 100
} catch {
    throw "Invalid regression registry JSON: $($_.Exception.Message)"
}

Require ([int]$registry.schemaVersion -ge 1) "Regression registry schemaVersion must be >= 1"
Require ($registry.integrationBranch -eq "vr-d3d9ex-focus") "Regression registry integrationBranch mismatch"
Require ([int]$registry.ledgerIssue -gt 0) "Regression ledger issue number missing"
Require ($registry.policy.eventHistory -eq "append-only") "Regression event history must be append-only"

$cases = @($registry.cases)
Require ($cases.Count -gt 0) "Regression registry must contain at least one case"
$keys = @{}
$history = Get-Content -Raw $historyPath

foreach ($case in $cases) {
    $key = [string]$case.key
    Require (-not [string]::IsNullOrWhiteSpace($key)) "Regression case missing key"
    Require (-not $keys.ContainsKey($key)) "Duplicate regression key: $key"
    $keys[$key] = $true

    Require (-not [string]::IsNullOrWhiteSpace([string]$case.title)) "Regression case $key missing title"
    Require (-not [string]::IsNullOrWhiteSpace([string]$case.status)) "Regression case $key missing status"
    Require (@($case.riskPaths).Count -gt 0) "Regression case $key missing riskPaths"
    Require (@($case.revalidationTriggers).Count -gt 0) "Regression case $key missing revalidationTriggers"
    Require ($null -ne $case.verifier) "Regression case $key missing verifier"
    Require (@($case.verifier.static).Count -gt 0) "Regression case $key missing static verifier"
    Require (@($case.verifier.runtime).Count -gt 0) "Regression case $key missing runtime verifier"
    Require ([int]$case.testLevel -ge 0 -and [int]$case.testLevel -le 4) "Regression case $key invalid testLevel"
    Require ([int]$case.recurrenceCount -ge 0) "Regression case $key invalid recurrenceCount"
    Require ($history.Contains($key)) "Problem history does not mention regression case $key"

    if ([string]$case.status -match "FIXED|DONE") {
        Require (@($case.fixReferences).Count -gt 0) "Fixed regression $key has no fixReferences"
        Require ([string]$case.rootCause.status -notmatch "UNKNOWN") "Fixed regression $key still has unknown root cause"
    }
}

Require ($keys.ContainsKey("VR-STARTUP-WHITE-001")) "Startup white-screen regression baseline missing"

Write-Host ("VR regression knowledge validation passed. cases={0}; ledgerIssue=#{1}" -f $cases.Count, $registry.ledgerIssue)
