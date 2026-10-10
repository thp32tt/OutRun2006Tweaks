param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot
)

$ErrorActionPreference = 'Stop'

$requiredTokens = @(
    'NativeDrawPathActive',
    'DrawIndexed',
    'Draw',
    'D3D11'
)

$forbiddenActivation = @(
    'NativeDrawPathActive = true',
    'NativeDrawPathActive=true',
    'enable_native_draw_path = true'
)

$files = Get-ChildItem -Path $SourceRoot -Recurse -File -Include *.cpp,*.hpp,*.h,*.ini,*.json

$matches = @()
foreach ($file in $files) {
    $text = Get-Content -Raw -LiteralPath $file.FullName
    foreach ($token in $requiredTokens) {
        if ($text.Contains($token)) {
            $matches += [pscustomobject]@{
                File = $file.FullName
                Token = $token
            }
        }
    }
}

$activationViolations = @()
foreach ($file in $files) {
    $text = Get-Content -Raw -LiteralPath $file.FullName
    foreach ($pattern in $forbiddenActivation) {
        if ($text.Contains($pattern)) {
            $activationViolations += [pscustomobject]@{
                File = $file.FullName
                Pattern = $pattern
            }
        }
    }
}

$result = [ordered]@{
    schema = 1
    check = 'DX11_DRAW_STATE_CONTRACT'
    source_root = $SourceRoot
    files_scanned = $files.Count
    evidence = $matches
    activation_violations = $activationViolations
    native_draw_activation_claim = if ($activationViolations.Count -eq 0) { 'DISABLED_OR_UNPROVEN' } else { 'REJECTED' }
}

$result | ConvertTo-Json -Depth 5

if ($activationViolations.Count -gt 0) {
    exit 1
}

exit 0
