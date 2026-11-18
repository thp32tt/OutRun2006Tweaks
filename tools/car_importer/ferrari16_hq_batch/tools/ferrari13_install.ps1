param(
    [string]$GameDir = "",
    [switch]$VerifyOnly,
    [switch]$Launch
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$manifestPath = Join-Path $root 'manifest.json'
if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Ferrari13 manifest missing" }
$m = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($m.Schema -ne 1 -or $m.CarCount -ne 13 -or $m.Status -ne 'STATIC_QA_PASS_NOT_QUEST3_TESTED') {
    throw "Unsupported or unverified Ferrari13 package"
}
$files = @($m.Files)
if ($files.Count -lt 28) { throw "Ferrari13 file-list is incomplete" }
function SafeRel([string]$rel) {
    if ([string]::IsNullOrWhiteSpace($rel) -or $rel -match '(^[\\/]|(^|[\\/])\.\.([\\/]|$)|:|[^\w./\\-])') {
        throw "Unsafe package relative path: $rel"
    }
    return ($rel -replace '/', '\')
}
function HashFile([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
foreach ($f in $files) {
    $srcRel = SafeRel ([string]$f.Source)
    $destRel = SafeRel ([string]$f.Target)
    $src = Join-Path $root $srcRel
    if (!(Test-Path -LiteralPath $src -PathType Leaf)) { throw "Missing source $srcRel" }
    if ((Get-Item -LiteralPath $src).Length -ne [long]$f.Bytes) {
        throw "File size mismatch: $srcRel"
    }
    if ((HashFile $src) -ne ([string]$f.Sha256).ToLowerInvariant()) {
        throw "File SHA256 mismatch: $srcRel"
    }
    if ([string]$f.Mode -notin @('always','missing-only')) {
        throw "Unknown file install mode: $srcRel"
    }
}
if ($VerifyOnly) {
    Write-Host "PASS: Ferrari13 all 13 bodies, 13 dashboards, integrated runtime and optional defaults verified. Nothing installed."
    return
}
if ([string]::IsNullOrWhiteSpace($GameDir)) {
    throw "Specify -GameDir pointing at a local folder containing OR2006C2C.EXE"
}
$game = (Resolve-Path -LiteralPath $GameDir).Path
$exe = Join-Path $game 'OR2006C2C.EXE'
if (!(Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "OR2006C2C.EXE not found. Game original executable is not included or modified."
}
$processes = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if ($processes) { throw "Exit OutRun and VR host before installing" }
$backup = Join-Path $game ('FERRARI13_PRIVATE_BACKUP_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
if (Test-Path -LiteralPath $backup) { throw "Existing backup path conflict" }
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$records = @()
foreach ($f in $files) {
    $dstRel = SafeRel ([string]$f.Target)
    $dst = Join-Path $game $dstRel
    $existed = Test-Path -LiteralPath $dst -PathType Leaf
    $originalSha = ''
    if ($existed) {
        $originalSha = HashFile $dst
        $save = Join-Path $backup $dstRel
        New-Item -ItemType Directory -Path (Split-Path -Parent $save) -Force | Out-Null
        Copy-Item -LiteralPath $dst -Destination $save -Force
        if ((HashFile $save) -ne $originalSha) {
            throw "Backup copy failed for $dstRel; original game not modified"
        }
    }
    $records += [pscustomobject]@{Path=$dstRel;Existed=$existed;OriginalSha256=$originalSha}
}
@{Schema=1;CarCount=13;Created=(Get-Date).ToString('o');Files=$records} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backup 'restore.json') -Encoding UTF8
try {
    foreach ($f in $files) {
        $src = Join-Path $root (SafeRel ([string]$f.Source))
        $dst = Join-Path $game (SafeRel ([string]$f.Target))
        if ([string]$f.Mode -eq 'missing-only' -and (Test-Path -LiteralPath $dst -PathType Leaf)) {
            continue
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -Force
        if ((HashFile $dst) -ne ([string]$f.Sha256).ToLowerInvariant()) {
            throw "Post-install SHA256 mismatch: $($f.Target)"
        }
    }
} catch {
    $cause = $_.Exception.Message
    foreach ($rec in $records) {
        $dst = Join-Path $game (SafeRel ([string]$rec.Path))
        if ($rec.Existed) {
            $src = Join-Path $backup (SafeRel ([string]$rec.Path))
            Copy-Item -LiteralPath $src -Destination $dst -Force
        } else {
            if (Test-Path -LiteralPath $dst -PathType Leaf) {
                Remove-Item -LiteralPath $dst -Force
            }
        }
    }
    throw "Ferrari13 installation reverted after error: $cause"
}
Write-Host "PASS: Ferrari13 private test models and dashboard overlays installed with SHA checks."
Write-Host "Backup: $backup"
Write-Host "Original executable untouched; 3 donor-only models were not installed or overwritten."
if ($Launch) {
    $args = @(
        '-VR.QuestCockpitV2Enabled=true',
        '-VR.F50ExternalModel=true',
        '-VR.ExternalFerrariTest=true',
        '-VR.QuestCockpitV2FullCar=true',
        '-VR.QuestCockpitV2NativeSeatProfile=true',
        '-VR.QuestCockpitV2ApkNativeCamera=true',
        '-VR.QuestCockpitV2GlassReflectionOff=true',
        '-VR.Telemetry=false',
        '-FileLogging=false'
    )
    Start-Process -FilePath $exe -WorkingDirectory $game -ArgumentList $args
}