param(
    [Parameter(Mandatory=$true)]
    [string]$HexBytes,
    [Parameter(Mandatory=$true)]
    [string]$ExpectedPrefix
)

$ErrorActionPreference = 'Stop'

$actual = (($HexBytes -split '\s+') | Where-Object { $_ }).ForEach({ $_.ToLowerInvariant() }) -join ' '
$expected = (($ExpectedPrefix -split '\s+') | Where-Object { $_ }).ForEach({ $_.ToLowerInvariant() }) -join ' '

if([string]::IsNullOrWhiteSpace($actual) -or [string]::IsNullOrWhiteSpace($expected)) {
    throw 'DXVK continuation byte validation requires non-empty byte sequences.'
}

if(-not $actual.StartsWith($expected)) {
    throw "DXVK continuation overlap mismatch. Expected prefix '$expected', received '$actual'."
}

[pscustomobject]@{
    contract = 'DXVK_CONTINUATION_WINDOW_PREFIX'
    status = 'PASS'
    validated_prefix = $expected
}
