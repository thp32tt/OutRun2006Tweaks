#Requires -Version 5.1
<#
 Creates an isolated, byte-checked copy of a WORKING official v0.03 installation.
 The original release directory is read-only. No /MIR and no destructive cleanup.
 Without -Create performs validation only.
#>
param(
  [Parameter(Mandatory=$true)][string]$ReleaseRoot,
  [Parameter(Mandatory=$true)][string]$TestRoot,
  [switch]$Create
)
$ErrorActionPreference='Stop'
$Expected=@{
  'OR2006C2C.EXE'='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
  'OutRun2006Tweaks.ini'='630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358'
  'dinput8.dll'='b4fc8d100c8716c12829f1defe76a959fc9953119ba792a8e72ca56ccec5cbe1'
  'outrun-vr-host.exe'='bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8'
}
function Sha([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function CheckRelease([string]$root) {
  foreach($name in $Expected.Keys) {
    $path=Join-Path $root $name
    if(!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing official release file: $path" }
    $actual=Sha $path
    if($actual -ne $Expected[$name]) {
      throw "Official v0.03 fingerprint mismatch: $name actual=$actual expected=$($Expected[$name]); refusing mixed/modified game."
    }
  }
}
$src=(Resolve-Path -LiteralPath $ReleaseRoot).Path.TrimEnd('\','/')
$dst=[System.IO.Path]::GetFullPath($TestRoot).TrimEnd('\','/')
if(!$dst -or $src.Equals($dst,[StringComparison]::OrdinalIgnoreCase) -or
   $dst.StartsWith($src+'\',[StringComparison]::OrdinalIgnoreCase) -or
   $src.StartsWith($dst+'\',[StringComparison]::OrdinalIgnoreCase)) {
  throw 'ReleaseRoot and TestRoot must be distinct, non-nested directories.'
}
if((Split-Path -Path $dst -Leaf) -notmatch '(?i)ferrari.*test') {
  throw 'The TEST folder name must contain Ferrari and Test (e.g. OutRun-Ferrari14-Test).'
}
CheckRelease $src
if(!$Create) {
  Write-Host 'PASS: official v0.03 source EXE/INI/DLL/host hashes verified.'
  Write-Host "VERIFY-ONLY. Add -Create to copy the full game to $dst."
  exit 0
}
if(Test-Path -LiteralPath $dst) {
  throw 'Target already exists; refusing to overwrite or merge a working game directory.'
}
New-Item -ItemType Directory -Path $dst -ErrorAction Stop | Out-Null
try {
  Get-ChildItem -LiteralPath $src -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $dst -Recurse -Force -ErrorAction Stop
  }
  CheckRelease $dst
  $marker=[ordered]@{
    Schema=1
    Purpose='FERRARI14_V003_ISOLATED_TEST_COPY'
    SourceRoot=$src
    TestRoot=$dst
    ReleaseTag='v0.03'
    ReleaseCommit='2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7'
    CreatedAt=(Get-Date).ToString('o')
  }
  ($marker | ConvertTo-Json -Depth 4) | Set-Content -LiteralPath (Join-Path $dst '.ferrari14-v003-testcopy.json') -Encoding UTF8
} catch {
  Write-Warning "Copy incomplete at $dst. Original release was not changed. Review or manually remove the incomplete TEST folder."
  throw
}
Write-Host "PASS: isolated v0.03 game copy prepared at $dst. Source unchanged."
