param(
    [Parameter(Mandatory=$true)][string]$GameDir,
    [Parameter(Mandatory=$true)][string]$BackupDir
)
$ErrorActionPreference='Stop'
$game=(Resolve-Path -LiteralPath $GameDir).Path
$backup=(Resolve-Path -LiteralPath $BackupDir).Path
$record=Join-Path $backup 'restore.json'
if (!(Test-Path -LiteralPath $record -PathType Leaf)) { throw 'Backup restore.json missing' }
$m=Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
if ($m.Schema -ne 1 -or $m.CarCount -ne 13) { throw 'Invalid Ferrari13 restore manifest' }
if (Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}) { throw 'Exit OutRun and VR host first' }
foreach ($f in @($m.Files)) {
    $rel=[string]$f.Path
    if ([string]::IsNullOrWhiteSpace($rel) -or $rel -match '(^[\\/]|(^|[\\/])\.\.([\\/]|$)|:|[^\w./\\-])') {
        throw "Unsafe backup path $rel"
    }
    $dst=Join-Path $game ($rel -replace '/', '\')
    $src=Join-Path $backup ($rel -replace '/', '\')
    if ($f.Existed) {
        if (!(Test-Path -LiteralPath $src -PathType Leaf) -or
            ((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -ne [string]$f.OriginalSha256)) {
            throw "Backup file missing/corrupt: $rel; refusing partial restore"
        }
    }
}
foreach ($f in @($m.Files)) {
    $rel=([string]$f.Path -replace '/', '\')
    $dst=Join-Path $game $rel
    if ($f.Existed) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $backup $rel) -Destination $dst -Force
    } elseif (Test-Path -LiteralPath $dst -PathType Leaf) {
        Remove-Item -LiteralPath $dst -Force
    }
}
Write-Host 'PASS: Ferrari13 previous files restored (original game executable was never replaced)'