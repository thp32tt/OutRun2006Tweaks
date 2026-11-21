#Requires -Version 5.1
# Real Windows PowerShell installer/restore control flow tested against an official
# v0.03 release copy and a NONEXECUTABLE MOCK DLL (not a VR driver runtime test).
param([Parameter(Mandatory=$true)][string]$RepoRoot,[Parameter(Mandatory=$true)][string]$ScratchRoot)
$ErrorActionPreference='Stop'
function Sha([string]$p) {(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Check([bool]$v,[string]$why) { if(!$v) {throw $why} }
$hashes=@{
 'OR2006C2C.EXE'='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
 'OutRun2006Tweaks.ini'='630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358'
 'dinput8.dll'='b4fc8d100c8716c12829f1defe76a959fc9953119ba792a8e72ca56ccec5cbe1'
 'outrun-vr-host.exe'='bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8'
}
$tools=Join-Path $RepoRoot 'tools\ferrari14'
foreach($name in @('PREPARE-FERRARI14-V003-TEST-COPY.ps1','APPLY-FERRARI14-V003-CLEAN.ps1','RESTORE-FERRARI14-V003-CLEAN.ps1')) {
 $file=Join-Path $tools $name
 $err=$null;$tokens=$null
 [System.Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$err) | Out-Null
 Check ($err.Count -eq 0) "Powershell parse error in $name"
 Check ((Get-Content -LiteralPath $file -Raw) -notmatch '(?im)^\s*\$host\s*=') 'Illegal read-only host variable assignment'
}
New-Item -ItemType Directory -Path $ScratchRoot -Force | Out-Null
$zip=Join-Path $ScratchRoot 'official-v003.zip'
Invoke-WebRequest -Uri 'https://github.com/thp32tt/OutRun2006Tweaks/releases/download/v0.03/OutRun2_VR_v0.03_Beta_Cockpit.zip' -OutFile $zip -UseBasicParsing
$expanded=Join-Path $ScratchRoot 'official-extracted'
Expand-Archive -LiteralPath $zip -DestinationPath $expanded -Force
$exes=@(Get-ChildItem -LiteralPath $expanded -Filter 'OR2006C2C.EXE' -File -Recurse)
Check ($exes.Count -eq 1) 'Expected one EXE in official release ZIP'
$release=$exes[0].DirectoryName
$observed=@{}
foreach($name in $hashes.Keys) {
 $actual=Sha (Join-Path $release $name)
 $observed[$name]=$actual
 Write-Host "OFFICIAL_RELEASE_ACTUAL name=$name sha256=$actual expected=$($hashes[$name])"
}
foreach($name in $hashes.Keys) {
 Check ($observed[$name] -eq $hashes[$name]) "Official fingerprint mismatch $name"
}
$target=Join-Path $ScratchRoot 'OutRun-Ferrari14-Test'
$prepare=Join-Path $tools 'PREPARE-FERRARI14-V003-TEST-COPY.ps1'
& $prepare -ReleaseRoot $release -TestRoot $target
Check (!(Test-Path -LiteralPath $target)) 'Verify-only copied files'
& $prepare -ReleaseRoot $release -TestRoot $target -Create
Check (Test-Path -LiteralPath (Join-Path $target '.ferrari14-v003-testcopy.json')) 'Test marker absent'
$package=Join-Path $ScratchRoot 'Mock-Package'
New-Item -ItemType Directory -Path (Join-Path $package 'PAYLOAD') -Force | Out-Null
$mock=Join-Path $package 'PAYLOAD\dinput8.dll'
[System.IO.File]::WriteAllBytes($mock,[System.Text.Encoding]::ASCII.GetBytes('MOCK_NOT_EXECUTABLE_TEST_BACKUP_ONLY'))
$patched=Sha $mock
foreach($name in @('APPLY-FERRARI14-V003-CLEAN.ps1','RESTORE-FERRARI14-V003-CLEAN.ps1','RUN-FERRARI14-V003-MODEL-OFF.cmd','RUN-FERRARI14-V003-575-ON.cmd','RUN-FERRARI14-V003-575-TRACE.cmd')) {
 Copy-Item -LiteralPath (Join-Path $tools $name) -Destination $package
}
@{Schema=1;PackageType='FERRARI14_V003_RELEASE_PARITY';ReleaseDllSha256=$hashes['dinput8.dll'];ReleaseHostSha256=$hashes['outrun-vr-host.exe'];PatchedDllSha256=$patched} |
 ConvertTo-Json | Set-Content -LiteralPath (Join-Path $package 'QA.json') -Encoding UTF8
$apply=Join-Path $package 'APPLY-FERRARI14-V003-CLEAN.ps1'
$restore=Join-Path $package 'RESTORE-FERRARI14-V003-CLEAN.ps1'
& $apply -GameRoot $target
Check ((Sha (Join-Path $target 'dinput8.dll')) -eq $hashes['dinput8.dll']) 'Verify-only changed runtime'
& $apply -GameRoot $target -Install
Check ((Sha (Join-Path $target 'dinput8.dll')) -eq $patched) 'Mock patch not installed'
$backups=@(Get-ChildItem -LiteralPath $target -Directory -Filter 'FERRARI14_V003_BACKUP_*')
Check ($backups.Count -eq 1) 'Expected exactly one backup'
& $restore -GameRoot $target -BackupFolder $backups[0].FullName
Check ((Sha (Join-Path $target 'dinput8.dll')) -eq $hashes['dinput8.dll']) 'Original DLL not restored'
foreach($name in @('RUN-FERRARI14-V003-MODEL-OFF.cmd','RUN-FERRARI14-V003-575-ON.cmd','RUN-FERRARI14-V003-575-TRACE.cmd')) {
 Check (!(Test-Path -LiteralPath (Join-Path $target $name))) "Rollback left launcher $name"
}
foreach($name in $hashes.Keys) {Check ((Sha (Join-Path $release $name)) -eq $hashes[$name]) "Official release changed $name"}
$marker=Join-Path $target '.ferrari14-v003-testcopy.json'
Rename-Item -LiteralPath $marker -NewName '.ferrari14-v003-testcopy.held'
$rejected=$false;try {& $apply -GameRoot $target} catch {$rejected=$true}
Check $rejected 'Markerless copy was accepted'
Rename-Item -LiteralPath (Join-Path $target '.ferrari14-v003-testcopy.held') -NewName '.ferrari14-v003-testcopy.json'
Add-Content -LiteralPath (Join-Path $target 'OutRun2006Tweaks.ini') -Value 'CI_INVALID_CONFIG'
$rejected=$false;try {& $apply -GameRoot $target} catch {$rejected=$true}
Check $rejected 'Modified INI was accepted'
Write-Host 'WINDOWS_POWERSHELL_CLEAN_RELEASE_COPY_MOCK_INSTALL_ROLLBACK_PASS'
