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

$disabledActivationEvidence = @(
    'NativeDrawPathActive=false',
    'NativeDrawPathActivation=DISABLED',
    'native_draw_path_activation_changed=false'
)

$extensions = @('*.cpp','*.hpp','*.h','*.json','*.md','*.ps1','*.ini','*.cmake')
$excludedDirectories = @('.git','out','build','node_modules')
$files = Get-ChildItem -Path $Root -Recurse -File -Include $extensions -ErrorAction SilentlyContinue |
    Where-Object {
        $relative = $_.FullName.Substring($Root.Length).TrimStart('\','/')
        -not ($excludedDirectories | Where-Object { $relative -like "$_/*" })
    }

$matches = @()
$forbiddenMatches = @()
$disabledMatches = @()
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
    foreach ($evidence in $disabledActivationEvidence) {
        if ($text -match [regex]::Escape($evidence)) {
            $disabledMatches += [pscustomobject]@{
                Evidence = $evidence
                File = $file.FullName.Substring($Root.Length).TrimStart('\','/')
            }
        }
    }
}

Write-Host "DX11_NATIVE_DRAW_GATE_STATIC_SCAN"
Write-Host "FilesScanned=$($files.Count)"
Write-Host "SignalsFound=$($matches.Count)"
Write-Host "DisabledEvidence=$($disabledMatches.Count)"
Write-Host "ForbiddenActivationClaims=$($forbiddenMatches.Count)"

$matches | Sort-Object Signal, File | Format-Table -AutoSize
$disabledMatches | Sort-Object Evidence, File | Format-Table -AutoSize
$forbiddenMatches | Sort-Object Claim, File | Format-Table -AutoSize

if ($matches.Count -eq 0) {
    throw 'No DX11 activation gate evidence markers found.'
}

if ($forbiddenMatches.Count -ne 0) {
    throw 'DX11 native draw activation claim detected without runtime evidence gate.'
}

if ($disabledMatches.Count -eq 0) {
    throw 'No dormant DX11 activation preservation evidence found.'
}

Write-Host 'RESULT=PASS_STATIC_EVIDENCE_PRESENT_DORMANT_GATE_PRESERVED'
Write-Host 'RUNTIME_VALIDATION=UNTESTED'
