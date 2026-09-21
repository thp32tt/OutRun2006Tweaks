param(
    [string]$Repository = $env:GITHUB_REPOSITORY,
    [string]$ResultSha = $env:GITHUB_SHA,
    [int]$LedgerIssue = 14,
    [int]$Attempts = 12,
    [int]$RetrySeconds = 5
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Require([bool]$Condition,[string]$Message){
    if(-not $Condition){throw $Message}
}

Require (-not [string]::IsNullOrWhiteSpace($Repository)) 'GitHub repository identity is missing'
Require ($Repository -match '^[^/]+/[^/]+$') "Invalid repository identity: $Repository"
Require ($ResultSha -match '^[0-9a-fA-F]{40}$') "ResultSha must be an exact 40-hex commit SHA"

$headers=@{
    Accept='application/vnd.github+json'
    'User-Agent'='OutRun2006Tweaks-ledger-verifier'
    'X-GitHub-Api-Version'='2022-11-28'
}
if($env:GITHUB_TOKEN){
    $headers.Authorization="Bearer $($env:GITHUB_TOKEN)"
}

function Get-LedgerComments {
    $all=@()
    for($page=1; $page -le 10; ++$page){
        $uri="https://api.github.com/repos/$Repository/issues/$LedgerIssue/comments?per_page=100&page=$page"
        $batch=@(Invoke-RestMethod -Headers $headers -Uri $uri -Method Get)
        $all += $batch
        if($batch.Count -lt 100){break}
    }
    return $all
}

$shaRegex=[regex]::Escape($ResultSha)
$matched=$null
for($attempt=1; $attempt -le $Attempts; ++$attempt){
    $comments=Get-LedgerComments
    $matched=@($comments | Where-Object {
        [string]$_.body -match "(?mi)^\s*resultSha:\s*`?$shaRegex`?\s*$"
    } | Select-Object -Last 1)

    if($matched.Count -gt 0){break}
    if($attempt -lt $Attempts){
        Write-Host "Issue #$LedgerIssue has no event for $ResultSha yet; retry $attempt/$Attempts"
        Start-Sleep -Seconds $RetrySeconds
    }
}

Require ($matched.Count -eq 1) "Issue #$LedgerIssue has no production-change event covering exact result SHA $ResultSha"
$body=[string]$matched[0].body

$requiredFields=@(
    'sourceMode','changedAtKst','baseSha','resultSha','changeSummary',
    'changedPaths','reason','relatedFindingOrRegressionKeys','validation',
    'runtimeTestRequired','nextAction'
)
foreach($field in $requiredFields){
    Require ($body -match "(?mi)^\s*${field}:\s*\S.+$") "Issue #$LedgerIssue event for $ResultSha missing/non-empty field: $field"
}

$sourceMode=([regex]::Match($body,'(?mi)^\s*sourceMode:\s*([^\r\n]+)$')).Groups[1].Value.Trim()
Require ($sourceMode -in @('SCHEDULED_D','CHAT_DIRECT','MANUAL')) "Invalid sourceMode in Issue #$LedgerIssue event: $sourceMode"

$baseSha=([regex]::Match($body,'(?mi)^\s*baseSha:\s*`?([0-9a-fA-F]{40})`?\s*$')).Groups[1].Value
Require ($baseSha -match '^[0-9a-fA-F]{40}$') "Issue #$LedgerIssue event has invalid baseSha"

$compareUri="https://api.github.com/repos/$Repository/compare/$baseSha...$ResultSha"
$compare=Invoke-RestMethod -Headers $headers -Uri $compareUri -Method Get
Require ([string]$compare.status -in @('ahead','identical')) "Ledger baseSha is not an ancestor/equal of resultSha: status=$($compare.status)"
Require ([int]$compare.ahead_by -ge 0) 'Invalid compare ahead_by'

Write-Host "Production ledger verification passed: issue=#$LedgerIssue result=$ResultSha base=$baseSha sourceMode=$sourceMode"
