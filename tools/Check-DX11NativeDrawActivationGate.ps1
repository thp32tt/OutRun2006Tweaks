# Static DX11 native draw activation gate analyzer
# Runtime validation remains separate. This tool only checks source/config evidence.

[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'

$requiredSignals = @(
    'NativeDrawPathActive',
    'NativeDrawPathActivation',
    'RUNTIME_VALIDATION=UNTESTED'
)

$forbiddenActivationClaims = @(
    'NATIVE_DRAW_PATH_ACTIVATED=true',
    'NativeDrawPathActive=true',
    'NativeDrawPathActivation=ENABLED'
)

$extensions = @('*.cpp','*.hpp','*.h','*.json','*.md','*.ps1')
$files = Get-ChildItem -Path $Root -Recurse -File -Include $extensions -ErrorAction SilentlyContinue

$matches = @()
$forbiddenMatches = @()
foreach ($file in $files) {
    $text = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    foreach ($signal in $requiredSignals) {
        if ($text -match [regex]::Escape($signal)) {
            $matches += [pscustomobject]@{
                Signal = $signal
                File = $file.FullName.Substring($Root.Length).TrimStart('\','/')
            }
        }
    }
    foreach ($claim in $forbiddenActivationClaims) {
        if ($text -match [regex]::Escape($claim)) {
            $forbiddenMatches += [pscustomobject]@{
                Claim = $claim
                File = $file.FullName.Substring($Root.Length).TrimStart('\','/')
            }
        }
    }
}

Write-Host "DX11_NATIVE_DRAW_GATE_STATIC_SCAN"
Write-Host "FilesScanned=$($files.Count)"
Write-Host "SignalsFound=$($matches.Count)"
Write-Host "ForbiddenActivationClaims=$($forbiddenMatches.Count)"

$matches | Sort-Object Signal, File | Format-Table -AutoSize
$forbiddenMatches | Sort-Object Claim, File | Format-Table -AutoSize

if ($matches.Count -eq 0) {
    throw 'No DX11 activation gate evidence markers found.'
}

if ($forbiddenMatches.Count -ne 0) {
    throw 'DX11 native draw activation claim detected without runtime evidence gate.'
}

Write-Host 'RESULT=PASS_STATIC_EVIDENCE_PRESENT'
Write-Host 'RUNTIME_VALIDATION=UNTESTED'
