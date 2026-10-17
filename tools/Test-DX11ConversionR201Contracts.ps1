# DX11 R201 conversion contract test.
# This is a static/source contract only. It does not enable native draw routing
# and it does not claim Quest 3/VDXR runtime validation.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

function Require-Text {
    param(
        [string]$File,
        [string]$Marker
    )

    $path = Join-Path $Root $File
    if (-not (Test-Path $path)) {
        throw "Missing DX11 contract file: $File"
    }

    $text = Get-Content $path -Raw
    if ($text -notmatch [regex]::Escape($Marker)) {
        throw "Missing DX11 contract marker '$Marker' in $File"
    }
}

# R201 fixed-function semantics require explicit TEMP provenance rather than
# silently treating RESULTARG TEMP as CURRENT.
Require-Text 'src/vr/d3d11/pipeline_translation.hpp' 'D3DTSS_RESULTARG may target CURRENT or TEMP'
Require-Text 'src/vr/d3d11/pipeline_translation.hpp' 'TEMP is readable from its D3D9 default transparent-black value'

# Keep the dormant conversion gate separate from runtime activation.
Require-Text 'docs/CONVERSION_LANE_STATE.json' 'native_draw_path_activation_changed'
Require-Text 'docs/CONVERSION_LANE_STATE.json' 'runtime_validation": "UNTESTED"'

Write-Output 'DX11_R201_CONTRACT=PASS'
Write-Output 'NATIVE_DRAW_PATH=UNCHANGED'
Write-Output 'RUNTIME_VALIDATION=UNTESTED'
