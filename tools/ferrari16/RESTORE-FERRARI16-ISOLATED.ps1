#Requires -Version 5.1
# Restore only the exact file bytes saved by the isolated installer.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$GameRoot,
      [Parameter(Mandatory=$true)][string]$BackupPath)
$ErrorActionPreference='Stop'
# A lexical path/manifest match is not physical isolation on Windows.
# Reject junctions/symlinks (including ancestors) before reads or writes.
function Assert-NoReparsePath([string]$p) {
    $current=[IO.Path]::GetFullPath($p)
    while($current) {
        $item=Get-Item -LiteralPath $current -Force -ErrorAction Stop
        if($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Reparse point is not allowed in isolated path: $current"
        }
        $current=[IO.Path]::GetDirectoryName($current)
    }
}
function Hash([string]$p) {
    if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "Missing file: $p"}
    Assert-NoReparsePath $p
    return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
}
$root=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\','/')
$backup=(Resolve-Path -LiteralPath $BackupPath).Path.TrimEnd('\','/')
Assert-NoReparsePath $root
Assert-NoReparsePath $backup
if(!$backup.StartsWith($root+'\FERRARI16_BACKUP_',[StringComparison]::OrdinalIgnoreCase) -or
   $backup.Substring($root.Length+1).Contains('\')){
    throw 'Backup must be a direct FERRARI16_BACKUP_* child of isolated test root.'
}
$markerPath=Join-Path $root '.ferrari16-isolated.json'
Assert-NoReparsePath $markerPath
Assert-NoReparsePath (Join-Path $backup 'manifest.json')
$m=Get-Content -LiteralPath $markerPath -Raw|ConvertFrom-Json
$b=Get-Content -LiteralPath (Join-Path $backup 'manifest.json') -Raw|ConvertFrom-Json
if($m.Schema -ne 1 -or $m.Purpose -ne 'FERRARI16_ISOLATED_V003_TEST_COPY' -or
   ![string]::Equals([string]$m.TestRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
   [string]::Equals([string]$m.SourceRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
   $b.Schema -ne 1 -or $b.Purpose -ne 'FERRARI16_ISOLATED_ROLLBACK' -or
   ![string]::Equals([string]$b.TestRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
   (Hash $markerPath) -ne $b.MarkerSha256){
    throw 'Rollback marker/target does not match.'
}
if(@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue).Count){
    throw 'Close game and host before restoring.'
}
# Validate the complete fixed launcher allowlist before resolving any path.
# A corrupt manifest must never authorize deleting arbitrary files.
$launchers=@('RUN-FERRARI16-V003-ALL-CARS.cmd',
             'RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd',
             'RUN-FERRARI16-V003-MODEL-OFF.cmd',
             'RUN-FERRARI16-V003-PBR-TRACE.cmd')
if($b.Launchers -isnot [pscustomobject] -or
   @($b.Launchers.PSObject.Properties).Count -ne $launchers.Count){
    throw 'Invalid rollback launcher map.'
}
foreach($entry in $b.Launchers.PSObject.Properties){
    if($launchers -cnotcontains $entry.Name -or
       $entry.Value -isnot [string] -or $entry.Value -cnotmatch '^[a-f0-9]{64}$'){
        throw 'Invalid rollback launcher entry.'
    }
}
# The backup hashes must match the independent PREPARE marker, not just
# the manifest alongside potentially damaged backup bytes.
if($b.OriginalDll -cnotmatch '^[a-f0-9]{64}$' -or
   $b.OriginalHost -cnotmatch '^[a-f0-9]{64}$' -or
   $b.OriginalDll -cne [string]$m.OriginalHashes.'dinput8.dll' -or
   $b.OriginalHost -cne [string]$m.OriginalHashes.'outrun-vr-host.exe'){
    throw 'Rollback original hashes do not match isolation marker.'
}
$dll=Join-Path $root 'dinput8.dll'
$hostExe=Join-Path $root 'outrun-vr-host.exe'
if((Hash $dll) -ne $b.PatchedDll -or (Hash $hostExe) -ne $b.PatchedHost){
    throw 'Installed payload modified: refusing overwrite.'
}
if((Hash (Join-Path $backup 'dinput8.dll')) -ne $b.OriginalDll -or
   (Hash (Join-Path $backup 'outrun-vr-host.exe')) -ne $b.OriginalHost){
    throw 'Rollback backup damaged.'
}
foreach($name in $launchers){
    $entry=$b.Launchers.PSObject.Properties[$name]
    if($null -eq $entry -or $entry.Name -cne $name -or
       (Hash (Join-Path $root $name)) -cne $entry.Value){
        throw "Launcher missing or modified: $name"
    }
}
Copy-Item -LiteralPath (Join-Path $backup 'dinput8.dll') -Destination $dll -Force -ErrorAction Stop
Copy-Item -LiteralPath (Join-Path $backup 'outrun-vr-host.exe') -Destination $hostExe -Force -ErrorAction Stop
if((Hash $dll) -ne $b.OriginalDll -or (Hash $hostExe) -ne $b.OriginalHost){
    throw 'Rollback restore hash mismatch.'
}
foreach($name in $launchers){
    Remove-Item -LiteralPath (Join-Path $root $name) -ErrorAction Stop
}
Write-Host 'PASS: isolated test copy restored. Working v0.03 was never touched.'
