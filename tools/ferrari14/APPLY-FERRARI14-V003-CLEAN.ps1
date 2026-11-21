#Requires -Version 5.1
# Ferrari14 v0.03 CLEAN release test-copy installer.
# Default is VERIFY ONLY; never modifies the official working release.
param([Parameter(Mandatory=$true)][string]$GameRoot,[switch]$Install)
$ErrorActionPreference='Stop'
function Sha([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
function AssertHash([string]$p,[string]$expected) {
  if(!(Test-Path -LiteralPath $p -PathType Leaf)) { throw "Required file missing: $p" }
  $actual=Sha $p
  if($actual -ne $expected) { throw "Fingerprint mismatch: $p actual=$actual expected=$expected" }
}
$officialExe='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
$officialIni='630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358'
$officialDll='b4fc8d100c8716c12829f1defe76a959fc9953119ba792a8e72ca56ccec5cbe1'
$officialVrHost='bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8'
$allowedModelHashes=@(
 '16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71',
 '222eca041b07623f7d489c5cb675464f43859939d865ff63e3f26b08df49683b',
 '275e6eb55819c0a89c39e23e13fadb4616f3b496792260f59970634167021acc'
)
$launchers=@(
 'RUN-FERRARI14-V003-MODEL-OFF.cmd',
 'RUN-FERRARI14-V003-575-ON.cmd',
 'RUN-FERRARI14-V003-575-TRACE.cmd'
)
$root=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\','/')
$markerPath=Join-Path $root '.ferrari14-v003-testcopy.json'
if(!(Test-Path -LiteralPath $markerPath -PathType Leaf)) { throw 'No isolated TEST copy marker. Run PREPARE-FERRARI14-V003-TEST-COPY.ps1 first.' }
$m=Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
if($m.Schema -ne 1 -or $m.Purpose -ne 'FERRARI14_V003_ISOLATED_TEST_COPY' -or
   ![string]::Equals([string]$m.TestRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
   [string]::Equals([string]$m.SourceRoot,$root,[StringComparison]::OrdinalIgnoreCase)) {
  throw 'Invalid marker / source equals target. Refuse any changes.'
}
AssertHash (Join-Path $root 'OR2006C2C.EXE') $officialExe
AssertHash (Join-Path $root 'OutRun2006Tweaks.ini') $officialIni
$vrHostPath=Join-Path $root 'outrun-vr-host.exe' # NEVER use $Host: read-only PowerShell automatic variable.
AssertHash $vrHostPath $officialVrHost
$dllPath=Join-Path $root 'dinput8.dll'
if(!(Test-Path -LiteralPath $dllPath -PathType Leaf)) {throw 'Existing runtime DLL missing'}
$qaFile=Join-Path $PSScriptRoot 'QA.json'
if(!(Test-Path -LiteralPath $qaFile -PathType Leaf)) {throw 'Package QA manifest missing'}
$qa=Get-Content -LiteralPath $qaFile -Raw | ConvertFrom-Json
if($qa.Schema -ne 1 -or $qa.PackageType -ne 'FERRARI14_V003_RELEASE_PARITY' -or
   $qa.ReleaseDllSha256 -ne $officialDll -or
   $qa.ReleaseHostSha256 -ne $officialVrHost -or
   [string]$qa.PatchedDllSha256 -notmatch '^[0-9a-f]{64}$' -or
   $qa.PatchedDllSha256 -eq $officialDll) {
  throw 'Unrecognized patch QA manifest; refuse to install.'
}
$payloadDll=Join-Path $PSScriptRoot 'PAYLOAD\dinput8.dll'
AssertHash $payloadDll ([string]$qa.PatchedDllSha256)
$existing=Sha $dllPath
if($existing -ne $officialDll) {
  if($existing -eq $qa.PatchedDllSha256) {
    Write-Host 'PASS: already installed, DLL hash matches this patch.'
    exit 0
  }
  throw "Only a CLEAN official v0.03 test copy is accepted. DLL=$existing"
}
$model=Join-Path $root 'ExternalCars\car_id_05.ovc'
if(Test-Path -LiteralPath $model -PathType Leaf) {
  $modelSha=Sha $model
  if($modelSha -notin $allowedModelHashes) { throw "Unrecognized 575 sidecar: $modelSha. Refusing to mix a different model." }
  Write-Host "Known, private 575 sidecar verified: $modelSha"
} else {
  Write-Warning 'No 575 OVC installed. Model ON will fall back to the native original (model OFF test still works).'
}
foreach($name in $launchers) {
  $source=Join-Path $PSScriptRoot $name
  if(!(Test-Path -LiteralPath $source -PathType Leaf)) {throw "Missing launcher in patch: $name"}
  if(Test-Path -LiteralPath (Join-Path $root $name)) {
    throw "Target already has $name. Never overwrite another launcher."
  }
}
Write-Host 'PASS: isolated official v0.03 EXE / INI / DLL / host, source DLL and test-copy marker verified.'
if(!$Install) {
  Write-Host 'VERIFY ONLY: add -Install after shutting down both game and VR host.'
  exit 0
}
if(@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue).Count) {
  throw 'Game or VR host is running; close both first.'
}
$backup=Join-Path $root ('FERRARI14_V003_BACKUP_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fffffff')+'_'+[guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $backup -ErrorAction Stop | Out-Null
$backupDll=Join-Path $backup 'dinput8.dll'
$backupHost=Join-Path $backup 'outrun-vr-host.exe'
Copy-Item -LiteralPath $dllPath -Destination $backupDll -ErrorAction Stop
Copy-Item -LiteralPath $vrHostPath -Destination $backupHost -ErrorAction Stop
AssertHash $backupDll $officialDll
AssertHash $backupHost $officialVrHost
$launcherHashes=@{}
foreach($name in $launchers) { $launcherHashes[$name]=Sha (Join-Path $PSScriptRoot $name) }
$manifest=[ordered]@{
  Schema=1; TargetRoot=$root; TestMarker=(Sha $markerPath)
  OriginalDll=$officialDll; PatchedDll=[string]$qa.PatchedDllSha256
  OriginalHost=$officialVrHost
  CreatedAt=(Get-Date).ToString('o')
  Launchers=$launcherHashes
}
($manifest | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath (Join-Path $backup 'manifest.json') -Encoding UTF8
try {
  Copy-Item -LiteralPath $payloadDll -Destination $dllPath -Force -ErrorAction Stop
  AssertHash $dllPath ([string]$qa.PatchedDllSha256)
  foreach($name in $launchers) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $root $name) -ErrorAction Stop
    AssertHash (Join-Path $root $name) ([string]$launcherHashes[$name])
  }
  AssertHash $vrHostPath $officialVrHost
  AssertHash (Join-Path $root 'OR2006C2C.EXE') $officialExe
  AssertHash (Join-Path $root 'OutRun2006Tweaks.ini') $officialIni
} catch {
  $originalError=$_
  Copy-Item -LiteralPath $backupDll -Destination $dllPath -Force -ErrorAction Stop
  AssertHash $dllPath $officialDll
  foreach($name in $launchers) {
    $dest=Join-Path $root $name
    if((Test-Path -LiteralPath $dest -PathType Leaf) -and
        (Sha $dest) -eq [string]$launcherHashes[$name]) {
      Remove-Item -LiteralPath $dest -ErrorAction Stop
    }
  }
  throw $originalError
}
Write-Host "PASS: release-parity test runtime installed. Reversible backup: $backup"
Write-Host 'Run model OFF first. Model ON is an explicitly unsafe experimental native-callback replacement.'
