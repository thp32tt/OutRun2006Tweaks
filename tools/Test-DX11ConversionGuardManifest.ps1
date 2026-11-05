# Static DX11 conversion guard manifest verifier.
# Validates branch-local conversion safety invariants without making runtime claims.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

$statePath = Join-Path $Root 'docs/CONVERSION_LANE_STATE.json'
if (-not (Test-Path $statePath)) {
    throw 'DX11 conversion lane state is missing.'
}

$stateText = Get-Content $statePath -Raw
$state = $stateText | ConvertFrom-Json

$checks = @(
    @('branch', ($state.branch -eq 'vr-dx11-native-r71')),
    @('lane', ($state.lane -eq 'DX11')),
    @('runtime_separation', ($state.latest_durable_task.runtime_validation -eq 'UNTESTED')),
    @('static_cursor', (-not [string]::IsNullOrWhiteSpace($state.independent_static_next_action)))
)

foreach ($check in $checks) {
    if (-not $check[1]) {
        throw ('DX11 guard manifest check failed: ' + $check[0])
    }
}

if ($stateText -match 'NativeDrawPathActive\s*"?\s*:\s*true') {
    throw 'DX11 guard manifest detected activation of native draw path.'
}

Write-Output 'DX11_CONVERSION_GUARD_MANIFEST=PASS'
Write-Output ('BRANCH=' + $state.branch)
Write-Output ('RUNTIME_VALIDATION=' + $state.latest_durable_task.runtime_validation)
