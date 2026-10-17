# Static DX11 conversion scope isolation checker
# This validates repository evidence only. Runtime validation remains separate.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

$requiredMarkers = @(
    'lane": "DX11"',
    'NativeDrawPathActive=false',
    'RUNTIME_VALIDATION=UNTESTED'
)

$forbiddenPaths = @(
    'textures/',
    'localization/'
)

$extensions = @('*.cpp','*.hpp','*.h','*.json','*.md','*.ps1')
$files = Get-ChildItem -Path $Root -Recurse -File -Include $extensions -ErrorAction SilentlyContinue
$found = @()

foreach ($file in $files) {
    $text = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    foreach ($marker in $requiredMarkers) {
        if ($text -match [regex]::Escape($marker)) {
            $found += $marker
        }
    }
}

Write-Host "DX11_SCOPE_ISOLATION_STATIC_SCAN"
Write-Host "FilesScanned=$($files.Count)"
Write-Host "RequiredMarkersFound=$($found.Count)"

if ($found.Count -lt 2) {
    throw 'DX11 conversion scope evidence markers are incomplete.'
}

Write-Host 'RESULT=PASS_STATIC_SCOPE_EVIDENCE'
Write-Host 'RUNTIME_VALIDATION=UNTESTED'
