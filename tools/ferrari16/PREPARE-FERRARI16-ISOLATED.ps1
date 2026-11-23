#Requires -Version 5.1
# Copy the user's existing verified v0.03 into a NEW isolated test folder.
# Never modify the original install or distribute the user's game files.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceRoot,
      [Parameter(Mandatory=$true)][string]$TestRoot)
$ErrorActionPreference='Stop'
function Hash([string]$p) {
    if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "Required file missing: $p"}
    return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
}
$known=[ordered]@{
    'OR2006C2C.exe'='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
    'dinput8.dll'='5d3c4fa550f3589323d1bddf65f475915f97b1bcdd3904ba50df865e002b7443'
    'outrun-vr-host.exe'='8c7e574214eb39a11db906e97465da77e69402bc7aeaeb835bc8e732ad3d661f'
    'OutRun2006Tweaks.ini'='630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358'
}
$source=(Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\','/')
$dest=[IO.Path]::GetFullPath($TestRoot).TrimEnd('\','/')
if([string]::Equals($source,$dest,[StringComparison]::OrdinalIgnoreCase) -or
   $dest.StartsWith($source+'\',[StringComparison]::OrdinalIgnoreCase) -or
   $source.StartsWith($dest+'\',[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Source/test folders must be separate; neither may be inside the other.'
}
if(Test-Path -LiteralPath $dest){throw 'Test folder must NOT exist; refusing overwrite.'}
if(@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue).Count){
    throw 'Close game and VR host before preparing an isolated test.'
}
foreach($name in $known.Keys){
    $actual=Hash (Join-Path $source $name)
    if($actual -ne $known[$name]){throw "v0.03 source hash mismatch for $name : $actual"}
}
New-Item -Path $dest -ItemType Directory -ErrorAction Stop | Out-Null
try {
    Get-ChildItem -LiteralPath $source -Force | ForEach-Object {
        if($_.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Reparse link in source root is not copied: $($_.FullName)"
        }
        Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse -Force -ErrorAction Stop
    }
    foreach($name in $known.Keys){
        if((Hash (Join-Path $dest $name)) -ne $known[$name]){
            throw "Test-copy integrity mismatch for $name"
        }
    }
    $marker=[ordered]@{Schema=1;Purpose='FERRARI16_ISOLATED_V003_TEST_COPY'
        SourceRoot=$source;TestRoot=$dest;OriginalHashes=$known
        CreatedUtc=[DateTime]::UtcNow.ToString('o')}
    ($marker|ConvertTo-Json -Depth 6) | Set-Content -LiteralPath (Join-Path $dest '.ferrari16-isolated.json') -Encoding UTF8
    Write-Host "PASS: isolated official v0.03 test copy created at $dest"
} catch {
    Write-Warning "Copy incomplete. Inspect/delete ONLY the new test folder: $dest"
    throw
}
