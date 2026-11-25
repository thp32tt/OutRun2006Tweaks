#Requires -Version 5.1
# Verify-only by default; installs ONLY into PREPARE-created isolated test copy.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$GameRoot,[switch]$Install)
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
# Hard links are not reparse points. A normal SHA256 match does not
# prove that overwriting this filename cannot mutate another directory.
function Assert-SingleLinkFile([string]$p) {
    Assert-NoReparsePath $p
    if(-not ('Ferrari16FileIdentity' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class Ferrari16FileIdentity {
    [StructLayout(LayoutKind.Sequential)]
    public struct Info {
        public uint Attributes, CreationLow, CreationHigh, AccessLow, AccessHigh;
        public uint WriteLow, WriteHigh, VolumeSerial, SizeHigh, SizeLow;
        public uint NumberOfLinks, FileIndexHigh, FileIndexLow;
    }
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GetFileInformationByHandle(SafeFileHandle file, out Info info);
}
'@
    }
    $stream=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,
        ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    try {
        $info=New-Object Ferrari16FileIdentity+Info
        if(-not [Ferrari16FileIdentity]::GetFileInformationByHandle($stream.SafeFileHandle,[ref]$info)) {
            throw "Cannot prove isolated file link count: $p"
        }
        if($info.NumberOfLinks -ne 1) {
            throw "Hard link is not allowed in isolated overwrite target: $p"
        }
    } finally {
        $stream.Dispose()
    }
}
function Hash([string]$p) {
    if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "Missing file: $p"}
    Assert-NoReparsePath $p
    return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
}
$root=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\','/')
Assert-NoReparsePath $root
$package=Split-Path -Parent $PSCommandPath
$markerPath=Join-Path $root '.ferrari16-isolated.json'
if(!(Test-Path -LiteralPath $markerPath -PathType Leaf)){
    throw 'No isolated marker. Never install directly into the working release.'
}
Assert-NoReparsePath $markerPath
$m=Get-Content -LiteralPath $markerPath -Raw|ConvertFrom-Json
if($m.Schema -ne 1 -or $m.Purpose -ne 'FERRARI16_ISOLATED_V003_TEST_COPY' -or
   ![string]::Equals([string]$m.TestRoot,$root,[StringComparison]::OrdinalIgnoreCase) -or
   [string]::Equals([string]$m.SourceRoot,$root,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Invalid isolation marker.'
}
$qaPath=Join-Path $package 'QA.json'
Assert-NoReparsePath $qaPath
$qa=Get-Content -LiteralPath $qaPath -Raw|ConvertFrom-Json
if($qa.Schema -ne 1 -or $qa.TaskId -ne 'EXT16-005' -or
   $qa.PackageType -ne 'FERRARI16_ISOLATED_STATIC_TEST_ONLY' -or
   [string]$qa.BuildSourceSha -cnotmatch '^[a-f0-9]{40}$' -or
   $qa.RuntimeValidation -ne 'UNTESTED' -or
   $qa.Quest3HardwarePass -ne $false -or
   $qa.Real16ModelAssetsValidated -ne $false -or
   $qa.ThirdPartyModelsBundled -ne $false) {
    throw 'Unsafe package QA identity; HMD claims cannot be promoted.'
}
# Match private_test_package.py's exact hashed-file contract. Never accept
# a partial/empty hash map or resolve an arbitrary manifest-supplied path.
$expectedPackageFiles=@(
    'PAYLOAD/dinput8.dll','PAYLOAD/outrun-vr-host.exe',
    'LAUNCHERS/RUN-FERRARI16-V003-ALL-CARS.cmd',
    'LAUNCHERS/RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd',
    'LAUNCHERS/RUN-FERRARI16-V003-MODEL-OFF.cmd',
    'LAUNCHERS/RUN-FERRARI16-V003-PBR-TRACE.cmd',
    'PREPARE-FERRARI16-ISOLATED.ps1','INSTALL-FERRARI16-ISOLATED.ps1',
    'RESTORE-FERRARI16-ISOLATED.ps1','COLLECT-FERRARI16-LOGS.ps1',
    'COPYING.GPL3','THIRD_PARTY_NOTICES.md','README_FIRST_KO.txt'
)
if($qa.ContentSha256 -isnot [pscustomobject]){
    throw 'Missing or invalid package hash map.'
}
$entries=@($qa.ContentSha256.PSObject.Properties)
if($entries.Count -ne $expectedPackageFiles.Count){
    throw 'Package hash map must cover every required file exactly once.'
}
foreach($entry in $entries){
    if($expectedPackageFiles -cnotcontains $entry.Name -or
       $entry.Value -isnot [string] -or $entry.Value -cnotmatch '^[a-f0-9]{64}$'){
        throw "Invalid package hash entry: $($entry.Name)"
    }
}
foreach($name in $expectedPackageFiles){
    $entry=$qa.ContentSha256.PSObject.Properties[$name]
    if($null -eq $entry -or $entry.Name -cne $name){
        throw "Missing package hash entry: $name"
    }
    if((Hash (Join-Path $package $name)) -cne $entry.Value){
        throw "Package payload SHA mismatch: $name"
    }
}
$payloadDll=Join-Path $package 'PAYLOAD\dinput8.dll'
$payloadHost=Join-Path $package 'PAYLOAD\outrun-vr-host.exe'
$sourceDll=Join-Path $root 'dinput8.dll'
$sourceHost=Join-Path $root 'outrun-vr-host.exe'
Assert-SingleLinkFile $sourceDll
Assert-SingleLinkFile $sourceHost
foreach($name in @('OR2006C2C.exe','OutRun2006Tweaks.ini','dinput8.dll','outrun-vr-host.exe')) {
    if((Hash (Join-Path $root $name)) -ne [string]$m.OriginalHashes.$name) {
        throw "Test-copy original changed: $name; refuse overwrite."
    }
}
$launchers=@('RUN-FERRARI16-V003-ALL-CARS.cmd',
             'RUN-FERRARI16-V003-ALL-CARS-TRACE.cmd',
             'RUN-FERRARI16-V003-MODEL-OFF.cmd',
             'RUN-FERRARI16-V003-PBR-TRACE.cmd')
foreach($name in $launchers){
    if(Test-Path -LiteralPath (Join-Path $root $name)){
        throw "Launcher already exists at test target: $name"
    }
}
if(!$Install){
    Write-Host "VERIFY PASS: exact-SHA package $($qa.BuildSourceSha); source untouched; use -Install."
    exit 0
}
if(@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue).Count){
    throw 'Close ALL game and host processes before install.'
}
$backup=Join-Path $root ('FERRARI16_BACKUP_'+[DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_ffff')+'_'+[guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -Path $backup -ItemType Directory -ErrorAction Stop|Out-Null
Copy-Item -LiteralPath $sourceDll -Destination (Join-Path $backup 'dinput8.dll') -ErrorAction Stop
Copy-Item -LiteralPath $sourceHost -Destination (Join-Path $backup 'outrun-vr-host.exe') -ErrorAction Stop
$launcherHashes=[ordered]@{}
foreach($name in $launchers){
    $launcherHashes[$name]=Hash (Join-Path (Join-Path $package 'LAUNCHERS') $name)
}
$backupManifest=[ordered]@{Schema=1;Purpose='FERRARI16_ISOLATED_ROLLBACK'
    TestRoot=$root;MarkerSha256=(Hash $markerPath);SourceSha=[string]$qa.BuildSourceSha
    OriginalDll=(Hash $sourceDll);OriginalHost=(Hash $sourceHost)
    PatchedDll=(Hash $payloadDll);PatchedHost=(Hash $payloadHost)
    Launchers=$launcherHashes}
($backupManifest|ConvertTo-Json -Depth 6)|
    Set-Content -LiteralPath (Join-Path $backup 'manifest.json') -Encoding UTF8
try {
    Copy-Item -LiteralPath $payloadDll -Destination $sourceDll -Force -ErrorAction Stop
    Copy-Item -LiteralPath $payloadHost -Destination $sourceHost -Force -ErrorAction Stop
    if((Hash $sourceDll) -ne $backupManifest.PatchedDll -or
       (Hash $sourceHost) -ne $backupManifest.PatchedHost){throw 'Patch post-copy hash mismatch.'}
    foreach($name in $launchers){
        $dst=Join-Path $root $name
        Copy-Item -LiteralPath (Join-Path (Join-Path $package 'LAUNCHERS') $name) -Destination $dst -ErrorAction Stop
        if((Hash $dst) -ne $launcherHashes[$name]){throw "Launcher mismatch: $name"}
    }
} catch {
    $original=$_
    Copy-Item -LiteralPath (Join-Path $backup 'dinput8.dll') -Destination $sourceDll -Force -ErrorAction Stop
    Copy-Item -LiteralPath (Join-Path $backup 'outrun-vr-host.exe') -Destination $sourceHost -Force -ErrorAction Stop
    foreach($name in $launchers){
        $dst=Join-Path $root $name
        if((Test-Path -LiteralPath $dst -PathType Leaf) -and
           (Hash $dst) -eq $launcherHashes[$name]){
            Remove-Item -LiteralPath $dst -ErrorAction Stop
        }
    }
    throw $original
}
Write-Host "PASS: isolated test runtime installed. Rollback backup: $backup"
Write-Host 'Do not claim Quest3 PASS until physical testing; log runtime stereo/PBR/fallback.'
