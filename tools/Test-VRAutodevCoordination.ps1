param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

function Require([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Read-Json([string]$RelativePath) {
    $path = Join-Path $RepoRoot $RelativePath
    Require (Test-Path $path) "Missing required file: $RelativePath"
    try {
        return Get-Content -Raw $path | ConvertFrom-Json -Depth 100
    } catch {
        throw "Invalid JSON in $RelativePath : $($_.Exception.Message)"
    }
}

$state = Read-Json "docs/VR_AUTODEV_STATE.json"
$queue = Read-Json "docs/VR_WORK_QUEUE.json"
$feedback = Read-Json "docs/VR_RUNTIME_FEEDBACK.json"

Require ($state.branch -eq "vr-d3d9ex-focus") "State branch must be vr-d3d9ex-focus"
Require ($state.coordination.integrationBranch -eq "vr-d3d9ex-focus") "Coordination integration branch mismatch"
Require ($state.coordination.reviewBranch -eq "vr-d3d9ex-review") "Review branch mismatch"
Require ($state.coordination.supportBranch -eq "vr-d3d9ex-support") "Support branch mismatch"
Require ($state.coordination.productionWriter -eq "D_INTEGRATION_PLANNER") "Only D may be production writer"
Require ($state.coordination.candidateWriter -eq "B_FIX") "Only B may own candidate writes"
Require ([int]$state.coordination.maxIndependentUnvalidatedRuntimeCandidates -eq 3) "Runtime candidate WIP cap must be 3"
Require ([int]$state.coordination.maxMateriallyDifferentFixAttempts -eq 2) "Fix attempt cap must be 2"

Require ($queue.integrationBranch -eq "vr-d3d9ex-focus") "Queue integration branch mismatch"
Require ($queue.owner -eq "D_INTEGRATION_PLANNER") "Queue owner must be D_INTEGRATION_PLANNER"
Require ($queue.policy.productionWriter -eq "D_INTEGRATION_PLANNER") "Queue production writer mismatch"
Require ($queue.policy.candidateWriter -eq "B_FIX") "Queue candidate writer mismatch"
Require ([int]$queue.policy.maxIndependentUnvalidatedRuntimeCandidates -eq 3) "Queue WIP cap must be 3"
Require ([int]$queue.policy.maxMateriallyDifferentFixAttempts -eq 2) "Queue fix-attempt cap must be 2"

$allowed = @("READY","IN_PROGRESS","NEEDS_VALIDATION","VALIDATED","NEEDS_POST_REVIEW","NEED_HMD_TEST","BLOCKED","DONE")
$ids = @{}
foreach ($item in @($queue.items)) {
    $id = [string]$item.id
    Require (-not [string]::IsNullOrWhiteSpace($id)) "Queue item missing id"
    Require (-not $ids.ContainsKey($id)) "Duplicate queue id: $id"
    $ids[$id] = $true
    Require ($allowed -contains [string]$item.status) "Invalid queue status $($item.status) for $id"
    Require ([int]$item.attempts -le 2) "Attempt cap exceeded for $id"
}
foreach ($item in @($queue.items)) {
    foreach ($dep in @($item.dependencies)) {
        Require ($ids.ContainsKey([string]$dep)) "Unknown dependency $dep referenced by $($item.id)"
    }
}

$candidateBranches = @($queue.candidateWip.candidateBranches)
Require ([int]$queue.candidateWip.activeUnvalidatedCount -eq $candidateBranches.Count) "candidateWip count does not match candidateBranches"
Require ($candidateBranches.Count -le 3) "More than 3 unvalidated runtime candidates"

Require ($feedback.integrationBranch -eq "vr-d3d9ex-focus") "Runtime feedback integration branch mismatch"
Require ($feedback.owner -eq "D_INTEGRATION_PLANNER") "Runtime feedback owner must be D"

$workflowPath = Join-Path $RepoRoot ".github/workflows/vr-dx9ex-active.yml"
Require (Test-Path $workflowPath) "Missing candidate validation workflow"
$workflow = Get-Content -Raw $workflowPath
Require ($workflow.Contains("'vr-d3d9ex-candidate/**'")) "Candidate branch trigger missing from vr-dx9ex-active.yml"
Require ($workflow.Contains('group: vr-dx9ex-active-${{ github.ref_name }}')) "Candidate validation concurrency is not branch-scoped"

$protocolPath = Join-Path $RepoRoot "docs/VR_AUTODEV_PROTOCOL.md"
Require (Test-Path $protocolPath) "Missing four-role protocol"

Write-Host "VR four-role coordination validation passed."
Write-Host ("Queue items={0}; active candidate WIP={1}; runtime sessions={2}" -f @($queue.items).Count, $candidateBranches.Count, @($feedback.sessions).Count)
