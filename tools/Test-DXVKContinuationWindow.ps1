param(
    [Parameter(Mandatory=$true)]
    [string]$HexBytes,
    [Parameter(Mandatory=$true)]
    [string]$ExpectedPrefix,
    [int]$MinimumByteCount = 7
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Normalize-Bytes([string]$Value) {
    $tokens = @($Value -split '\s+' | Where-Object { $_ })
    if ($tokens.Count -eq 0) {
        throw 'DXVK continuation byte validation requires non-empty byte sequences.'
    }
    foreach ($token in $tokens) {
        if ($token -notmatch '^[0-9a-fA-F]{2}$') {
            throw "Invalid byte token: $token"
        }
    }
    return (($tokens | ForEach-Object { $_.ToLowerInvariant() }) -join ' ')
}

$actual = Normalize-Bytes $HexBytes
$expected = Normalize-Bytes $ExpectedPrefix

if (($actual -split ' ').Count -lt $MinimumByteCount) {
    throw "DXVK continuation window is shorter than required: $actual"
}

if(-not $actual.StartsWith($expected)) {
    throw "DXVK continuation overlap mismatch. Expected prefix '$expected', received '$actual'."
}

[pscustomobject]@{
    contract = 'DXVK_CONTINUATION_WINDOW_PREFIX'
    status = 'PASS'
    byte_count = ($actual -split ' ').Count
    validated_prefix = $expected
}
