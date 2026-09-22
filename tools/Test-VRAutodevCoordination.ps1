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
Require ($state.coordination.reviewBranches.A -eq "vr-d3d9ex-review-a") "A review branch mismatch"
Require ($state.coordination.reviewBranches.B -eq "vr-d3d9ex-review-b") "B review branch mismatch"
Require ($state.coordination.reviewBranches.C -eq "vr-d3d9ex-review-c") "C review branch mismatch"
Require (@($state.coordination.reviewOnlyRoles).Count -eq 3) "A/B/C review-only role set mismatch"

$canonicalDWriter = [string]$state.coordination.productionWriter
Require (-not [string]::IsNullOrWhiteSpace($canonicalDWriter)) "Canonical D production writer is missing"
Require ($canonicalDWriter -eq "D_IMPLEMENT_BUILD_VALIDATE_INTEGRATE") "Canonical D production writer must be D_IMPLEMENT_BUILD_VALIDATE_INTEGRATE"
Require ($state.coordination.candidateWriter -eq $canonicalDWriter) "State candidate writer must match canonical D writer"
Require ([int]$state.coordination.maxIndependentUnvalidatedRuntimeCandidates -eq 3) "Runtime candidate WIP cap must be 3"
Require ([int]$state.coordination.maxMateriallyDifferentFixAttempts -eq 2) "Fix attempt cap must be 2"

Require ($queue.integrationBranch -eq "vr-d3d9ex-focus") "Queue integration branch mismatch"
Require ($queue.owner -eq $canonicalDWriter) "Queue owner must match canonical D writer"
Require ($queue.policy.productionWriter -eq $canonicalDWriter) "Queue production writer mismatch"
Require ($queue.policy.candidateWriter -eq $canonicalDWriter) "Queue candidate writer mismatch"
Require ($queue.policy.queueWriter -eq $canonicalDWriter) "Queue writer mismatch"
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

$legacyRoles = @("D_INTEGRATION_PLANNER","B_FIX","C_VALIDATION","A_REVIEW","C_PERF_REVIEW","B_RENDER_REVIEW","A_ARCH_REVIEW")
foreach ($item in @($queue.items)) {
    $role = [string]$item.preferredRole
    Require ($role -notin $legacyRoles) "Legacy active role remains in queue for $($item.id): $role"
}

$candidateBranches = @($queue.candidateWip.candidateBranches)
Require ([int]$queue.candidateWip.activeUnvalidatedCount -eq $candidateBranches.Count) "candidateWip count does not match candidateBranches"
Require ($candidateBranches.Count -le 3) "More than 3 unvalidated runtime candidates"

Require ($feedback.integrationBranch -eq "vr-d3d9ex-focus") "Runtime feedback integration branch mismatch"
Require ($feedback.owner -eq $canonicalDWriter) "Runtime feedback owner must match canonical D writer"

Require ($null -ne $state.productionChangeLogging) "Missing productionChangeLogging state contract"
Require ([int]$state.productionChangeLogging.ledgerIssue -eq 14) "Production change ledger must be Issue #14"
Require ([bool]$state.productionChangeLogging.directChatUsesDTransactionContract) "Direct chat writes must use the D transaction contract"
Require ([bool]$state.productionChangeLogging.mandatoryAfterProductionCommit) "Production change logging must be mandatory after commit"
Require ($state.productionChangeLogging.logCheckpoint -eq "C4.5_LOG") "Production change logging checkpoint must be C4.5_LOG"
$sourceModes = @($state.productionChangeLogging.appliesTo)
Require ($sourceModes -contains "SCHEDULED_D") "SCHEDULED_D logging mode missing"
Require ($sourceModes -contains "CHAT_DIRECT") "CHAT_DIRECT logging mode missing"
Require ($sourceModes -contains "MANUAL") "MANUAL logging mode missing"
Require ([int]$state.productionChangeLogging.runtimeProblemAlsoUpdates.regressionLedgerIssue -eq 13) "Runtime regression ledger must remain Issue #13"

$workflowPath = Join-Path $RepoRoot ".github/workflows/vr-dx9ex-active.yml"
Require (Test-Path $workflowPath) "Missing candidate validation workflow"
$workflow = Get-Content -Raw $workflowPath
Require ($workflow.Contains("'vr-d3d9ex-candidate/**'")) "Candidate branch trigger missing from vr-dx9ex-active.yml"
Require ($workflow.Contains('group: vr-dx9ex-active-${{ github.ref_name }}')) "Candidate validation concurrency is not branch-scoped"

$protocolPath = Join-Path $RepoRoot "docs/VR_AUTODEV_PROTOCOL.md"
Require (Test-Path $protocolPath) "Missing four-role protocol"

Write-Host "VR four-role coordination validation passed."
Write-Host ("Queue items={0}; active candidate WIP={1}; runtime sessions={2}" -f @($queue.items).Count, $candidateBranches.Count, @($feedback.sessions).Count)
