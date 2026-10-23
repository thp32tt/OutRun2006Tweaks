# Static DX11 conversion cursor contract test.
# This verifies that the conversion lane exposes a resumable static-work cursor
# without allowing runtime activation claims.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

$statePath = Join-Path $Root 'docs/CONVERSION_LANE_STATE.json'
if (-not (Test-Path $statePath)) {
    Write-Error 'DX11 conversion state file is missing.'
}

$stateText = Get-Content $statePath -Raw
$state = $stateText | ConvertFrom-Json

if ($state.branch -ne 'vr-dx11-native-r71') {
    Write-Error ('Unexpected branch: ' + $state.branch)
}

if ($state.lane -ne 'DX11') {
    Write-Error ('Unexpected lane: ' + $state.lane)
}

if ([string]::IsNullOrWhiteSpace($state.independent_static_next_action)) {
    Write-Error 'Independent static next action cursor is missing.'
}

if ($state.latest_durable_task.runtime_validation -ne 'UNTESTED') {
    Write-Error 'Runtime validation must remain separated from static evidence.'
}

if ($stateText -match '"NativeDrawPathActive"\s*:\s*true') {
    Write-Error 'Static cursor test detected native draw activation.'
}

Write-Output 'DX11_STATE_CURSOR_CONTRACT=PASS'
Write-Output 'NATIVE_DRAW_PATH_ACTIVATION=DISABLED'
Write-Output ('TASK=' + $state.latest_durable_task.task_id)
Write-Output ('RUNTIME_VALIDATION=' + $state.latest_durable_task.runtime_validation)
