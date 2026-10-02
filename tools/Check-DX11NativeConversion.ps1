# Static DX11 conversion guard.
# This intentionally does not enable the native draw path. It checks source evidence
# used by the DX11 conversion lane and reports missing contract markers.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

$requiredPaths = @(
    'AGENTS.md',
    'docs/CONVERSION_LANE_STATE.json',
    'src'
)

$missing = @()
foreach ($path in $requiredPaths) {
    if (-not (Test-Path (Join-Path $Root $path))) {
        $missing += $path
    }
}

if ($missing.Count -gt 0) {
    Write-Error ('DX11 static contract missing: ' + ($missing -join ', '))
}

$state = Get-Content (Join-Path $Root 'docs/CONVERSION_LANE_STATE.json') -Raw | ConvertFrom-Json

if ($state.lane -ne 'DX11') {
    Write-Error 'Conversion lane is not DX11.'
}

if ($state.task_liveness.normal_success_requires -notcontains 'SUBSTANTIVE_C2_REQUIRED') {
    Write-Error 'DX11 task contract does not require substantive implementation.'
}

Write-Output 'DX11_STATIC_CONVERSION_GUARD=PASS'
Write-Output ('BRANCH=' + $state.branch)
Write-Output ('TASK=' + $state.latest_durable_task.task_id)
Write-Output ('RUNTIME_VALIDATION=' + $state.latest_durable_task.runtime_validation)
