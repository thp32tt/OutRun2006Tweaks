$ErrorActionPreference = 'Stop'
$game = Split-Path -Parent $MyInvocation.MyCommand.Path
$backup = Join-Path $game 'VR_SAFE_LAUNCH_BACKUP_20261101'
if (!(Test-Path -LiteralPath $backup)) { throw "No backup folder: $backup" }
if (Get-Process -Name OR2006C2C -ErrorAction SilentlyContinue) { throw 'Close the game first.' }
if (Get-Process -Name outrun-vr-host -ErrorAction SilentlyContinue) { throw 'Close the host first.' }
$names = @('dinput8.dll','outrun-vr-host.exe','RUN_DX9EX_TEST.cmd','Run-DX9ExFocusTest.ps1','DX9EX_VARIANT.txt')
foreach ($name in $names) {
    $saved = Join-Path $backup $name
    $absent = $saved + '.absent'
    $target = Join-Path $game $name
    if (Test-Path -LiteralPath $saved) {
        Copy-Item -LiteralPath $saved -Destination $target -Force -ErrorAction Stop
        Write-Host "Restored $name"
    } elseif (Test-Path -LiteralPath $absent) {
        if (Test-Path -LiteralPath $target) {
            $moved = Join-Path $backup ("safe-installed-" + $name)
            if (Test-Path -LiteralPath $moved) { throw "Existing disabled copy: $moved. Manual review required." }
            Move-Item -LiteralPath $target -Destination $moved -ErrorAction Stop
        }
        Write-Host "Disabled newly introduced $name"
    } else {
        Write-Warning "No saved original state for $name; left unchanged"
    }
}
Write-Host 'Restore completed. Original game executable and pre-existing INI were untouched.'
