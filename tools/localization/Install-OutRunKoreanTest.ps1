# OutRun 2006 HD Korean TEST_ONLY canary patch. Do not install as a release.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$GameDirectory,
    [switch]$ConfirmTestOnly,
    [switch]$ApplyAll,
    [ValidateRange(1,200)][int]$CanaryCount=5,
    [switch]$AllowMissingSource,
    [switch]$Rollback,
    [string]$BackupDirectory
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Hash([string]$path) {
    (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function CheckName([string]$path) {
    if ($path -notmatch '^textures/load/(?:(Keyboard|PlayStation|Switch|Xbox)/)?[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.dds$' -or $path.Contains('..')) {
        throw "Unsafe DDS name: $path"
    }
}
function CheckNoLinks([string]$root,[string]$path) {
    $partPath = $root
    foreach ($part in ($path -split '/')) {
        $partPath = Join-Path $partPath $part
        if ((Test-Path -LiteralPath $partPath) -and ((Get-Item -LiteralPath $partPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Link in game destination not permitted: $partPath"
        }
    }
}
if (-not $ConfirmTestOnly) {
    throw "Must pass -ConfirmTestOnly. This package is NOT visually or runtime approved."
}
$root = (Resolve-Path -LiteralPath $GameDirectory).Path
if (-not (Test-Path -LiteralPath (Join-Path $root 'OR2006C2C.exe'))) {
    throw "Expected OutRun game root containing OR2006C2C.exe"
}
$m = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'TEST_ONLY_INSTALL_MANIFEST.json') -Encoding UTF8 -Raw | ConvertFrom-Json
if ($m.schema -ne "outrun.korean.hd-preview-install.v1" -or $m.status -ne "TEST_ONLY_NOT_RELEASE_APPROVED" -or $m.release_approved -ne $false -or $m.runtime_validation -ne "UNTESTED") {
    throw "Bad TEST_ONLY manifest; refusing install"
}
$iniFile = Join-Path $root 'OutRun2006Tweaks.ini'
if (-not (Test-Path -LiteralPath $iniFile)) { throw "Tweaks INI absent. Game loader not verified." }
$ini = Get-Content -LiteralPath $iniFile -Raw
if ($ini -notmatch '(?im)^\s*UITextureReplacement\s*=\s*true\s*$') { throw "UITextureReplacement must be true" }
if ($ini -notmatch '(?im)^\s*TextureBaseFolder\s*=\s*textures\s*$') { throw "This patch supports only TextureBaseFolder=textures" }
if ($Rollback) {
    if (-not $BackupDirectory) { throw "-BackupDirectory required for rollback" }
    $backup = (Resolve-Path -LiteralPath $BackupDirectory).Path
    $j = Get-Content -LiteralPath (Join-Path $backup 'rollback.json') -Encoding UTF8 -Raw | ConvertFrom-Json
    if ($j.schema -ne "outrun.korean.rollback.v1" -or $j.game_root -ne $root) { throw "Rollback journal root mismatch" }
    # Validate all current and backup bytes BEFORE restoring anything.
    foreach ($entry in $j.entries) {
        CheckName $entry.path
        CheckNoLinks $root $entry.path
        $dst = Join-Path $root ($entry.path.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $dst) -or (Hash $dst) -ne $entry.installed_sha256) { throw "DDS has changed since test install: $dst" }
        if ($entry.original_sha256) {
            $prior = Join-Path $backup ($entry.path.Replace('/', '\'))
            if (-not (Test-Path -LiteralPath $prior) -or (Hash $prior) -ne $entry.original_sha256) { throw "Invalid backup: $prior" }
        }
    }
    foreach ($entry in $j.entries) {
        $dst = Join-Path $root ($entry.path.Replace('/', '\'))
        if ($entry.original_sha256) {
            Copy-Item -LiteralPath (Join-Path $backup ($entry.path.Replace('/', '\'))) -Destination $dst -Force
        } else {
            Remove-Item -LiteralPath $dst -Force
        }
    }
    Write-Output ("TEST_ONLY_ROLLBACK_OK: " + $j.entries.Count + " DDS")
    exit 0
}
$files = @($m.files | Sort-Object path)
if (-not $ApplyAll) { $files = @($files | Select-Object -First $CanaryCount) }
if ($files.Count -eq 0) { throw "No DDS atlas in preview package" }
$checks = @()
# Fail closed before changing a single game DDS.
foreach ($file in $files) {
    CheckName $file.path
    CheckNoLinks $root $file.path
    $rel = $file.path.Replace('/', '\')
    $src = Join-Path $PSScriptRoot $rel
    $dst = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $src) -or (Hash $src) -ne $file.test_only_dds_sha256) {
        throw "Staged Korean DDS SHA mismatch: $rel"
    }
    $oldHash = $null
    if (Test-Path -LiteralPath $dst) {
        $oldHash = Hash $dst
        if ($oldHash -ne $file.original_hd_sha256) {
            throw "Existing HD DDS is customized or unexpected; refusing overwrite: $rel"
        }
    } elseif (-not $AllowMissingSource) {
        throw "Pinned original HD DDS absent: $rel; require explicit -AllowMissingSource to create"
    }
    $checks += [pscustomobject]@{path=$file.path; source=$src; target=$dst; old=$oldHash; new=$file.test_only_dds_sha256}
}
if (-not $BackupDirectory) { $BackupDirectory = Join-Path $root ('_KoreanTestBackups\' + (Get-Date -Format 'yyyyMMdd_HHmmss')) }
if (Test-Path -LiteralPath $BackupDirectory) { throw "Select a new backup directory" }
New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
foreach ($c in $checks) {
    if ($c.old) {
        $backupDst = Join-Path $BackupDirectory ($c.path.Replace('/', '\'))
        New-Item -ItemType Directory -Path (Split-Path -Parent $backupDst) -Force | Out-Null
        Copy-Item -LiteralPath $c.target -Destination $backupDst -Force
        if ((Hash $backupDst) -ne $c.old) { throw "Backup SHA mismatch; installation stopped" }
    }
}
$j = [pscustomobject]@{
    schema="outrun.korean.rollback.v1"
    game_root=$root
    entries=@($checks | ForEach-Object {
        [pscustomobject]@{path=$_.path; original_sha256=$_.old; installed_sha256=$_.new}
    })
}
$j | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $BackupDirectory 'rollback.json') -Encoding UTF8
$installed = @()
try {
    foreach ($c in $checks) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $c.target) -Force | Out-Null
        $tmp = $c.target + ".korean_tmp"
        Copy-Item -LiteralPath $c.source -Destination $tmp -Force
        if ((Hash $tmp) -ne $c.new) { throw "Staged DDS corrupted: $($c.path)" }
        Move-Item -LiteralPath $tmp -Destination $c.target -Force
        $installed += $c
        if ((Hash $c.target) -ne $c.new) { throw "Installed DDS SHA mismatch: $($c.path)" }
    }
} catch {
    foreach ($c in $installed) {
        if ($c.old) { Copy-Item -LiteralPath (Join-Path $BackupDirectory ($c.path.Replace('/', '\'))) -Destination $c.target -Force }
        elseif (Test-Path -LiteralPath $c.target) { Remove-Item -LiteralPath $c.target -Force }
    }
    throw
}
Write-Output ("TEST_ONLY_APPLIED: " + $installed.Count + " atlases")
Write-Output ("BACKUP: " + $BackupDirectory)
Write-Output "To restore: .\Install-OutRunKoreanTest.ps1 -GameDirectory <game> -ConfirmTestOnly -Rollback -BackupDirectory <backup>"
