# DX11 conversion evidence probe.
# Offline static helper: verifies conversion evidence without enabling native draw.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

$required = @(
    'AGENTS.md',
    'docs/CONVERSION_LANE_STATE.json',
    'tools/Check-DX11NativeConversion.ps1',
    'CMakeLists.txt'
)

foreach ($item in $required) {
    if (-not (Test-Path (Join-Path $Root $item))) {
        throw "DX11 evidence file missing: $item"
    }
}

$state = Get-Content (Join-Path $Root 'docs/CONVERSION_LANE_STATE.json') -Raw | ConvertFrom-Json

if ($state.lane -ne 'DX11') {
    throw "Unexpected conversion lane: $($state.lane)"
}

if ($state.branch -ne 'vr-dx11-native-r71') {
    throw "Unexpected branch state: $($state.branch)"
}

if ($state.latest_durable_task.runtime_validation -ne 'UNTESTED') {
    throw 'Runtime validation must remain separate from offline evidence.'
}

$stateText = Get-Content (Join-Path $Root 'docs/CONVERSION_LANE_STATE.json') -Raw
if ($stateText -match 'NativeDrawPathActive"\s*:\s*true') {
    throw 'Native draw activation evidence detected.'
}

Write-Output 'DX11_CONVERSION_EVIDENCE_PROBE=PASS'
Write-Output ('TASK=' + $state.latest_durable_task.task_id)
Write-Output ('RUNTIME_VALIDATION=' + $state.latest_durable_task.runtime_validation)
