param(
    [Parameter(Mandatory=$true)]
    [string]$ReportPath,

    [Parameter(Mandatory=$true)]
    [int]$ExpectedInstructionCount
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ReportPath)) {
    throw "DXVK continuation report not found: $ReportPath"
}

$report = Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json

$required = @(
    'proof_start_rva',
    'probe_end_rva',
    'instruction_count',
    'branch_targets',
    'capture_edge_matches'
)

foreach ($name in $required) {
    if ($null -eq $report.$name) {
        throw "Missing continuation evidence field: $name"
    }
}

if ($report.capture_edge_matches -ne $true) {
    throw "DXVK continuation capture edge validation failed"
}

if ([int]$report.instruction_count -ne $ExpectedInstructionCount) {
    throw "Unexpected instruction count: $($report.instruction_count)"
}

if ($report.branch_targets.Count -eq 0) {
    throw "No resolved branch targets recorded"
}

Write-Output "DXVK_CONTINUATION_EVIDENCE=PASS"
Write-Output "PROOF_RANGE=$($report.proof_start_rva)..$($report.probe_end_rva)"
Write-Output "INSTRUCTION_COUNT=$($report.instruction_count)"
