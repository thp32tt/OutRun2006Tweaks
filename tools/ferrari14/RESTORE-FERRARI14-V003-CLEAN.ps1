#Requires -Version 5.1
# Strict rollback of a Ferrari14 v0.03 release-parity test-copy installation.
param([Parameter(Mandatory=$true)][string]$GameRoot,
      [Parameter(Mandatory=$true)][string]$BackupFolder)
$ErrorActionPreference='Stop'
function Sha([string]$p) {return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function AssertHash([string]$p,[string]$v) {
  if(!(Test-Path -LiteralPath $p -PathType Leaf) -or (Sha $p) -ne $v) {
    throw "Rollback SHA mismatch: $p"
  }
}
$root=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\','/')
$backup=(Resolve-Path -LiteralPath $BackupFolder).Path.TrimEnd('\','/')
$manifestPath=Join-Path $backup 'manifest.json'
if(!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) {throw 'Missing restore manifest'}
$m=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if($m.Schema -ne 1 -or
  ![string]::Equals([string]$m.TargetRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
  !$backup.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) {
  throw 'Restore path or schema mismatch'
}
$marker=Join-Path $root '.ferrari14-v003-testcopy.json'
AssertHash $marker ([string]$m.TestMarker)
$mark=Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
if($mark.Purpose -ne 'FERRARI14_V003_ISOLATED_TEST_COPY' -or
   ![string]::Equals([string]$mark.TestRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
   [string]::Equals([string]$mark.SourceRoot,$root,[StringComparison]::OrdinalIgnoreCase)) {
  throw 'Cannot restore on an unmarked or working release folder'
}
$dll=Join-Path $root 'dinput8.dll'
$vrHostPath=Join-Path $root 'outrun-vr-host.exe' # $Host is a read-only automatic variable.
$backupDll=Join-Path $backup 'dinput8.dll'
$backupHost=Join-Path $backup 'outrun-vr-host.exe'
AssertHash $dll ([string]$m.PatchedDll)
AssertHash $vrHostPath ([string]$m.OriginalHost)
AssertHash $backupDll ([string]$m.OriginalDll)
AssertHash $backupHost ([string]$m.OriginalHost)
foreach($p in $m.Launchers.PSObject.Properties) {
  AssertHash (Join-Path $root $p.Name) ([string]$p.Value)
}
if(@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue).Count) {
  throw 'Close game and host first.'
}
Copy-Item -LiteralPath $backupDll -Destination $dll -Force -ErrorAction Stop
AssertHash $dll ([string]$m.OriginalDll)
foreach($p in $m.Launchers.PSObject.Properties) {
  Remove-Item -LiteralPath (Join-Path $root $p.Name) -ErrorAction Stop
}
AssertHash $vrHostPath ([string]$m.OriginalHost)
Write-Host 'PASS: exact official v0.03 DLL restored. EXE/INI/host never modified. Test-copy marker preserved.'
