param(
    [Parameter(Mandatory = $true)]
    [string]$GhidraHome,
    [string]$ExePath = "",
    [string]$OutputDir = "",
    [switch]$NoDecompile
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$ContractPath = Join-Path $RepoRoot "docs\\VR_BINARY_CONTRACT.json"
$VerifierPath = Join-Path $RepoRoot "tools\\verify_vr_binary_contract.py"
$BuilderPath = Join-Path $PSScriptRoot "build_exe_map.py"
$SemanticsPath = Join-Path $PSScriptRoot "seed_semantics.json"

if (-not (Test-Path $ContractPath)) {
    throw "Missing binary contract: $ContractPath"
}

$Contract = Get-Content $ContractPath -Raw | ConvertFrom-Json
$ExpectedSha = [string]$Contract.canonicalExe.sha256
$SourceUrl = [string]$Contract.canonicalExe.sourceUrl
$Sha12 = $ExpectedSha.Substring(0, 12)

if ([string]::IsNullOrWhiteSpace($ExePath)) {
    $CacheDir = Join-Path $env:TEMP "OutRun2006Tweaks\\reverse"
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    $ExePath = Join-Path $CacheDir "OR2006C2C-$Sha12.EXE"
    if (-not (Test-Path $ExePath)) {
        Write-Host "Downloading canonical OR2006C2C.EXE..."
        Invoke-WebRequest -UseBasicParsing -Uri $SourceUrl -OutFile $ExePath
    }
}

$ExePath = (Resolve-Path $ExePath).Path

Write-Host "Verifying canonical executable contract..."
$VerifyArgs = @(
    $VerifierPath,
    "--exe", $ExePath,
    "--manifest", $ContractPath,
    "--source-root", $RepoRoot
)
& python @VerifyArgs
if ($LASTEXITCODE -ne 0) {
    throw "Canonical EXE verification failed."
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $RepoRoot "reverse\\OR2006C2C\\generated\\$Sha12"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path

$AnalyzeHeadless = Join-Path $GhidraHome "support\\analyzeHeadless.bat"
if (-not (Test-Path $AnalyzeHeadless)) {
    throw "analyzeHeadless.bat not found: $AnalyzeHeadless"
}

$ProjectRoot = Join-Path $env:TEMP ("OutRunGhidra-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $ProjectRoot | Out-Null

$Mode = if ($NoDecompile) { "nodecompile" } else { "decompile" }
$ProjectName = "OutRunMap_$Sha12"

Write-Host "Running Ghidra whole-program analysis ($Mode)..."
try {
    $GhidraArgs = @(
        $ProjectRoot,
        $ProjectName,
        "-import", $ExePath,
        "-overwrite",
        "-scriptPath", $PSScriptRoot,
        "-postScript", "ExportOutRunMap.java", $OutputDir, $Mode,
        "-analysisTimeoutPerFile", "1800",
        "-max-cpu", [string][Environment]::ProcessorCount,
        "-deleteProject"
    )
    & $AnalyzeHeadless @GhidraArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Ghidra analyzeHeadless failed with exit code $LASTEXITCODE"
    }
}
finally {
    if (Test-Path $ProjectRoot) {
        Remove-Item -LiteralPath $ProjectRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$DbPath = Join-Path $OutputDir "outrun_exe_map.sqlite"
Write-Host "Building SQLite knowledge map..."
$BuildArgs = @(
    $BuilderPath,
    "--export-dir", $OutputDir,
    "--db", $DbPath,
    "--semantics", $SemanticsPath,
    "--contract", $ContractPath
)
& python @BuildArgs
if ($LASTEXITCODE -ne 0) {
    throw "SQLite map build failed."
}

$DbHash = (Get-FileHash $DbPath -Algorithm SHA256).Hash.ToLowerInvariant()
$Meta = [ordered]@{
    schemaVersion = 1
    canonicalExeSha256 = $ExpectedSha
    database = [IO.Path]::GetFileName($DbPath)
    databaseSha256 = $DbHash
    generatedAtUtc = [DateTime]::UtcNow.ToString("o")
    decompiled = (-not $NoDecompile)
}
$Meta | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $OutputDir "map_build.json")

Write-Host ""
Write-Host "EXE knowledge map ready:"
Write-Host "  $DbPath"
Write-Host ""
Write-Host "Examples:"
Write-Host ('  python tools\\reverse\\exequery.py --db "{0}" 0x2D762' -f $DbPath)
Write-Host ('  python tools\\reverse\\exequery.py --db "{0}" HUD' -f $DbPath)
Write-Host ('  python tools\\reverse\\exequery.py --db "{0}" "rank marker"' -f $DbPath)
