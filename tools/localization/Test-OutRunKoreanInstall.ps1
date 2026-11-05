# Windows-only isolated smoke tests. NEVER uses user's actual OutRun installation.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = Join-Path $env:RUNNER_TEMP ("outrun-korean-smoke-" + [guid]::NewGuid().ToString("N"))
$game = Join-Path $root "game"
$package = Join-Path $root "package"
$ddsRel = "textures\load\spr_demo\12345678_64x64.dds"
$origin = Join-Path $game $ddsRel
$newFile = Join-Path $package $ddsRel
New-Item -ItemType Directory -Path (Split-Path -Parent $origin) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $newFile) -Force | Out-Null
[IO.File]::WriteAllBytes((Join-Path $game "OR2006C2C.exe"), [byte[]](1,2,3,4))
@"
[Graphics]
TextureBaseFolder = textures
UITextureReplacement = true
"@ | Set-Content -LiteralPath (Join-Path $game "OutRun2006Tweaks.ini") -Encoding UTF8
$rawOriginal = [Text.Encoding]::ASCII.GetBytes("DDS source-original-pinned")
$rawTranslated = [Text.Encoding]::ASCII.GetBytes("DDS korean-preview-TEST_ONLY")
[IO.File]::WriteAllBytes($origin, $rawOriginal)
[IO.File]::WriteAllBytes($newFile, $rawTranslated)
$originalHash = (Get-FileHash -LiteralPath $origin -Algorithm SHA256).Hash.ToLowerInvariant()
$newHash = (Get-FileHash -LiteralPath $newFile -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest = @{
    schema = "outrun.korean.hd-preview-install.v1"
    status = "TEST_ONLY_NOT_RELEASE_APPROVED"
    release_approved = $false
    runtime_validation = "UNTESTED"
    files = @(@{
        path="textures/load/spr_demo/12345678_64x64.dds"
        original_hd_sha256=$originalHash
        test_only_dds_sha256=$newHash
        orientation="NORMAL"
        painted_roi_ids=@("Q012_1234567890abcdef")
        held_roi_ids=@()
    })
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $package "TEST_ONLY_INSTALL_MANIFEST.json") -Encoding UTF8
$installer = Join-Path $package "Install-OutRunKoreanTest.ps1"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Install-OutRunKoreanTest.ps1") -Destination $installer -Force
$backup = Join-Path $root "backup"
& $installer -GameDirectory $game -ConfirmTestOnly -BackupDirectory $backup
if ((Get-FileHash -LiteralPath $origin -Algorithm SHA256).Hash.ToLowerInvariant() -ne $newHash) {
    throw "TEST_INSTALL_HASH_MISMATCH"
}
if (-not (Test-Path -LiteralPath (Join-Path $backup "rollback.json"))) { throw "NO_ROLLBACK_JOURNAL" }
& $installer -GameDirectory $game -ConfirmTestOnly -Rollback -BackupDirectory $backup
if ((Get-FileHash -LiteralPath $origin -Algorithm SHA256).Hash.ToLowerInvariant() -ne $originalHash) {
    throw "ROLLBACK_ORIGINAL_HASH_MISMATCH"
}
# Mutating any original source must stop before installation.
[IO.File]::WriteAllBytes($origin,[Text.Encoding]::ASCII.GetBytes("customized-resource"))
$expectedFailure = $false
try {
    & $installer -GameDirectory $game -ConfirmTestOnly -BackupDirectory (Join-Path $root "bad-backup")
} catch {
    if ($_.Exception.Message -like "*refusing overwrite*") { $expectedFailure = $true }
    else { throw }
}
if (-not $expectedFailure) { throw "CUSTOM_SOURCE_WAS_NOT_HELD" }
Write-Output "WINDOWS_KOREAN_CANARY_INSTALL_ROLLBACK_PRECHECK_PASS"
