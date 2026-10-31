param([string]$GameDirectory = "", [switch]$InstallOnly)
$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$payload = Join-Path $source 'payload'
$names = @('dinput8.dll','outrun-vr-host.exe','RUN_DX9EX_TEST.cmd','Run-DX9ExFocusTest.ps1','DX9EX_VARIANT.txt')
foreach ($name in $names) {
    if (!(Test-Path -LiteralPath (Join-Path $payload $name))) {
        throw "Incomplete package: $name. Extract the entire ZIP before running."
    }
}
if (!$GameDirectory) {
    if (Test-Path (Join-Path $source 'OR2006C2C.EXE')) { $GameDirectory = $source }
    elseif (Test-Path (Join-Path (Split-Path -Parent $source) 'OR2006C2C.EXE')) {
        $GameDirectory = Split-Path -Parent $source
    }
    else { $GameDirectory = Read-Host 'Full game folder containing OR2006C2C.EXE' }
}
$GameDirectory = $GameDirectory.Trim('"', ' ')
if (!$GameDirectory) { throw 'Game folder is required.' }
$gameRoot = (Resolve-Path -LiteralPath $GameDirectory -ErrorAction Stop).Path
if (!(Test-Path (Join-Path $gameRoot 'OR2006C2C.EXE'))) {
    throw "OR2006C2C.EXE missing from $gameRoot"
}
if (Get-Process -Name OR2006C2C -ErrorAction SilentlyContinue) { throw 'Close the game first.' }
if (Get-Process -Name outrun-vr-host -ErrorAction SilentlyContinue) { throw 'Close the old VR host first.' }
$backup = Join-Path $gameRoot 'VR_SAFE_LAUNCH_BACKUP_20261101'
New-Item -ItemType Directory -Force -Path $backup | Out-Null
foreach ($name in $names) {
    $target = Join-Path $gameRoot $name
    $saved = Join-Path $backup $name
    $absent = $saved + '.absent'
    if (!(Test-Path -LiteralPath $saved) -and !(Test-Path -LiteralPath $absent)) {
        if (Test-Path -LiteralPath $target) {
            Copy-Item -LiteralPath $target -Destination $saved -ErrorAction Stop
            if ((Get-Item -LiteralPath $target).Length -ne (Get-Item -LiteralPath $saved).Length) {
                throw "Backup failed validation ($name); no test binaries were installed."
            }
        } else {
            Set-Content -LiteralPath $absent -Value 'ABSENT_BEFORE_SAFE_INSTALL' -Encoding ascii
        }
    }
}
foreach ($name in $names) {
    Copy-Item -LiteralPath (Join-Path $payload $name) -Destination (Join-Path $gameRoot $name) -Force -ErrorAction Stop
}
foreach ($name in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')) {
    $target = Join-Path $gameRoot $name
    $ref = Join-Path (Join-Path $source 'reference_ini') $name
    if (!(Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $ref)) {
        Copy-Item -LiteralPath $ref -Destination $target -ErrorAction Stop
    }
}
foreach ($name in @('RUN_INSTALLED_SAFE.cmd','RESTORE_PREVIOUS.cmd','RESTORE_PREVIOUS.ps1')) {
    Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $gameRoot $name) -Force -ErrorAction Stop
}
Write-Host "SAFE R26 VR binaries installed. Backups: $backup"
Write-Host 'Existing game EXE and INI were not overwritten.'
Write-Host 'Official DX9Ex runner: RUN_DX9EX_TEST.cmd (includes required VR flags and logging).'
if (!$InstallOnly) {
    Write-Host 'Activate Quest/VDXR. Starting ORIGINAL DX9Ex runner, not the VR helper window.'
    $launcher = Join-Path $gameRoot 'RUN_DX9EX_TEST.cmd'
    Start-Process -FilePath $launcher -WorkingDirectory $gameRoot -Wait
}
