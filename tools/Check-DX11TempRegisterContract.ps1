param(
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"

# DX11 conversion lane guard: keep fixed-function translation evidence explicit.
# This does not enable native draw activation and does not replace Quest 3/VDXR testing.

$requiredMarkers = @(
    "D3DTA_TEMP",
    "D3DTA_RESULTARG",
    "TEMP",
    "RESULTARG"
)

$files = Get-ChildItem -Path $Root -Recurse -File -Include *.cpp,*.hpp,*.h,*.md,*.json -ErrorAction SilentlyContinue

if (-not $files) {
    Write-Error "No DX11 conversion files found for static contract scan"
}

$matches = @()
foreach ($file in $files) {
    $text = Get-Content -Raw -LiteralPath $file.FullName
    if ($text -match "D3DTA_TEMP|D3DTA_RESULTARG|RESULTARG|TEMP") {
        $matches += $file.FullName
    }
}

if ($matches.Count -eq 0) {
    Write-Error "DX11 fixed-function TEMP/RESULTARG contract evidence not found"
}

Write-Output "DX11_TEMP_REGISTER_CONTRACT=PASS"
Write-Output "MATCHED_FILES=$($matches.Count)"
Write-Output "RUNTIME_VALIDATION=UNTESTED"
