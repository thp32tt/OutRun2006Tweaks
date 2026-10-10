# Static DX11 conversion guard.
# This intentionally does not enable the native draw path. It checks source evidence
# used by the DX11 conversion lane and reports missing contract markers.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

function Require-TextMarker {
    param(
        [string]$File,
        [string]$Marker,
        [string]$Message
    )

    $content = Get-Content (Join-Path $Root $File) -Raw
    if ($content -notmatch [regex]::Escape($Marker)) {
        Write-Error $Message
    }
}

function Require-StateValue {
    param(
        [object]$Object,
        [string]$Path,
        [string]$Expected,
        [string]$Message
    )

    $cursor = $Object
    foreach ($part in $Path.Split('.')) {
        $cursor = $cursor.$part
    }

    if ($cursor -ne $Expected) {
        Write-Error ($Message + ' Actual=' + $cursor)
    }
}

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

$statePath = Join-Path $Root 'docs/CONVERSION_LANE_STATE.json'
$state = Get-Content $statePath -Raw | ConvertFrom-Json

Require-StateValue $state 'lane' 'DX11' 'Conversion lane is not DX11.'
Require-StateValue $state 'branch' 'vr-dx11-native-r71' 'Unexpected DX11 branch state.'
Require-StateValue $state 'latest_durable_task.runtime_validation' 'UNTESTED' 'Hardware validation must remain separated from static validation.'
Require-StateValue $state 'latest_durable_task.checkpoint' 'C6_STATE' 'DX11 state is not persisted at a resumable checkpoint.'

if ($state.task_liveness.normal_success_requires -notcontains 'SUBSTANTIVE_C2_REQUIRED') {
    Write-Error 'DX11 task contract does not require substantive implementation.'
}

$stateText = Get-Content $statePath -Raw
if ($stateText -notmatch 'NativeDrawPath') {
    Write-Error 'DX11 conversion state does not expose native draw path gate evidence.'
}

if ($stateText -notmatch 'independent_static_next_action') {
    Write-Error 'DX11 conversion state does not expose a resumable static work cursor.'
}

if ($stateText -match 'NativeDrawPathActive"\s*:\s*true') {
    Write-Error 'DX11 guard detected native draw activation in static state.'
}

# Guard the DX11 build lane from silently losing its dedicated semantic probes.
$cmake = Join-Path $Root 'CMakeLists.txt'
if (-not (Test-Path $cmake)) {
    Write-Error 'CMakeLists.txt missing for DX11 target verification.'
}
Require-TextMarker 'CMakeLists.txt' 'dx11_fixed_function_shader_semantics' 'DX11 fixed-function semantic target is missing.'
Require-TextMarker 'CMakeLists.txt' 'dx11_input_layout_semantics' 'DX11 input-layout semantic target is missing.'
Require-TextMarker 'CMakeLists.txt' 'dx11_shader_linkage_probe' 'DX11 shader linkage probe target is missing.'

Write-Output 'DX11_STATIC_CONVERSION_GUARD=PASS'
Write-Output 'DX11_STATE_INVARIANT_GUARD=PASS'
Write-Output 'NATIVE_DRAW_PATH_GATE=STATIC_EVIDENCE_PRESENT'
Write-Output 'DORMANT_ACTIVATION_GUARD=PASS'
Write-Output 'SEMANTIC_PROBE_TARGET_GUARD=PASS'
Write-Output ('BRANCH=' + $state.branch)
Write-Output ('TASK=' + $state.latest_durable_task.task_id)
Write-Output ('RUNTIME_VALIDATION=' + $state.latest_durable_task.runtime_validation)
