param(
    [Parameter(Mandatory=$true)]
    [string]$EvidenceFile,
    [string]$ExpectedStart = '0x00182F7E',
    [string]$ExpectedEnd = '0x00182FBE'
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path $EvidenceFile -PathType Leaf)) {
    throw "Evidence file not found: $EvidenceFile"
}

$raw = Get-Content $EvidenceFile -Raw
if ([string]::IsNullOrWhiteSpace($raw)) {
    throw 'Evidence file is empty'
}

$json = $raw | ConvertFrom-Json

$start = [string]$json.provenance_start_rva
$end = [string]$json.probe_end_rva

if ($start -ne $ExpectedStart) {
    throw "Unexpected provenance start RVA: $start"
}

if ($end -ne $ExpectedEnd) {
    throw "Unexpected probe end RVA: $end"
}

if ($json.predecessor_exact -ne $true) {
    throw 'Predecessor exact-match proof is missing'
}

if ($json.provenance_status -notmatch '^EXACT_') {
    throw "Non-exact provenance status: $($json.provenance_status)"
}

[pscustomobject]@{
    status = 'PASS'
    provenance_start_rva = $start
    probe_end_rva = $end
    predecessor_exact = [bool]$json.predecessor_exact
    provenance_status = [string]$json.provenance_status
} | ConvertTo-Json -Compress
