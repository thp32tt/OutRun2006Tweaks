# Windows-only compatibility smoke: both PowerShell syntax and PBR VerifyOnly.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$copyRun=Join-Path $repo 'QuestCockpit-CopyRun.ps1'
$restore=Join-Path $repo 'QuestCockpit-CopyRestore.ps1'
foreach($file in @($copyRun,$restore)) {
    $tokens=$null
    $errors=$null
    $null=[System.Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
    if($errors.Count -gt 0){
        $info=($errors|ForEach-Object{$_.ToString()}) -join '; '
        throw "PowerShell syntax error in $file : $info"
    }
}
$root=Join-Path $env:RUNNER_TEMP ('dino-pbr-copyrun-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -Force|Out-Null
try {
    Copy-Item -LiteralPath $copyRun -Destination (Join-Path $root 'QuestCockpit-CopyRun.ps1')
    $payload=Join-Path $root 'QUEST_APK_COPYRUN_PAYLOAD'
    foreach($part in @('backend','model','scripts','defaults')) {
        New-Item -ItemType Directory -Path (Join-Path $payload $part) -Force|Out-Null
    }
    function Make-StubPe([string]$dest,[int]$machine) {
        $bytes=[byte[]]::new(256)
        $bytes[0]=0x4d;$bytes[1]=0x5a
        [BitConverter]::GetBytes([int]128).CopyTo($bytes,0x3c)
        [BitConverter]::GetBytes([uint32]0x4550).CopyTo($bytes,128)
        [BitConverter]::GetBytes([uint16]$machine).CopyTo($bytes,132)
        [IO.File]::WriteAllBytes($dest,$bytes)
    }
    $gameDll=Join-Path $payload 'backend/dinput8.dll'
    $hostExe=Join-Path $payload 'backend/outrun-vr-host.exe'
    Make-StubPe $gameDll 0x14c
    Make-StubPe $hostExe 0x8664
    $sha='0123456789abcdef0123456789abcdef01234567'
    Set-Content -LiteralPath (Join-Path $payload 'backend/SOURCE_SHA.txt') -Value $sha -Encoding ascii
    Set-Content -LiteralPath (Join-Path $payload 'backend/HOST_BUILD_SOURCE_SHA.txt') -Value $sha -Encoding ascii
    Set-Content -LiteralPath (Join-Path $payload 'backend/VARIANT_ID.txt') -Value 'ACTIVE_R26_R43_R44' -Encoding ascii
    foreach($file in @('Run-OutRunVRTest.ps1','Select-OutRunVRBackend.ps1',
        'OutRunVR-TestProfiles.ps1','Collect-OutRunVRLogs.ps1',
        'Collect-OutRunVRLogs.cmd','Analyze-OutRunVRSession.ps1',
        'Run-QuestCockpitV2-CrashDiag.ps1','analyze_outrun_assets.py')) {
        Set-Content -LiteralPath (Join-Path $payload ('scripts/'+$file)) -Value '# synthetic fixture' -Encoding ascii
    }
    foreach($file in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')) {
        Set-Content -LiteralPath (Join-Path $payload ('defaults/'+$file)) -Value '# synthetic fixture' -Encoding ascii
    }
    $model=[byte[]]::new(64)
    [Text.Encoding]::ASCII.GetBytes('OVRCABH3').CopyTo($model,0)
    [BitConverter]::GetBytes([uint32]3).CopyTo($model,8)
    $modelPath=Join-Path $payload 'model/Dino246_Cockpit_LHD_v15_PBR.ovc'
    [IO.File]::WriteAllBytes($modelPath,$model)
    $identity=@{
        SourceSha=$sha;HostSourceSha=$sha;VariantId='ACTIVE_R26_R43_R44';
        GameDllSha256=(Get-FileHash -LiteralPath $gameDll -Algorithm SHA256).Hash.ToLowerInvariant();
        HostExeSha256=(Get-FileHash -LiteralPath $hostExe -Algorithm SHA256).Hash.ToLowerInvariant();
        DinoPbrModelSha256=(Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $idFile=Join-Path $payload 'IDENTITY.json'
    $identity|ConvertTo-Json|Set-Content -LiteralPath $idFile -Encoding UTF8
    & (Join-Path $root 'QuestCockpit-CopyRun.ps1') -Mode PBR -VerifyOnly
    if(-not $?){throw 'PBR VerifyOnly failed unexpectedly.'}
    if(Test-Path (Join-Path $root 'QUEST_APK_COPYRUN_ORIGINAL_BACKUP')) {
        throw 'VerifyOnly must not create a backup or change a game folder.'
    }
    # Fail-closed: source marker mismatch before any installation mutation.
    Set-Content -LiteralPath (Join-Path $payload 'backend/HOST_BUILD_SOURCE_SHA.txt') -Value 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' -Encoding ascii
    $rejected=$false
    try {& (Join-Path $root 'QuestCockpit-CopyRun.ps1') -Mode PBR -VerifyOnly}
    catch { $rejected=($_.Exception.Message -match 'source marker') }
    if(-not $rejected){throw 'Mismatched OpenXR source marker was not rejected.'}
    Set-Content -LiteralPath (Join-Path $payload 'backend/HOST_BUILD_SOURCE_SHA.txt') -Value $sha -Encoding ascii
    # Fail-closed: sidecar content mismatch before any installation mutation.
    $bytes=[IO.File]::ReadAllBytes($modelPath)
    $bytes[35] = 1
    [IO.File]::WriteAllBytes($modelPath,$bytes)
    $rejected=$false
    try {& (Join-Path $root 'QuestCockpit-CopyRun.ps1') -Mode PBR -VerifyOnly}
    catch { $rejected=($_.Exception.Message -match 'PBR OVC3 sidecar') }
    if(-not $rejected){throw 'Incorrect OVC3 model hash was not rejected.'}
    if(Test-Path (Join-Path $root 'QUEST_APK_COPYRUN_ORIGINAL_BACKUP')) {
        throw 'Failed verify must not write backup files.'
    }
    # The real install path is tested against a completely synthetic game
    # directory: no user's EXE, data, VR runtime or stable OVC2 is touched.
    [IO.File]::WriteAllBytes($modelPath,$model)
    $original='USER_STABLE_OVC2_SENTINEL'
    $stableModel=Join-Path $root 'Dino246_Cockpit_LHD_v15.ovc'
    Set-Content -LiteralPath $stableModel -Value $original -Encoding ascii
    Set-Content -LiteralPath (Join-Path $root 'OR2006C2C.EXE') -Value 'GAME_EXE_SENTINEL' -Encoding ascii
    Set-Content -LiteralPath (Join-Path $root 'dinput8.dll') -Value 'PREVIOUS_USER_DLL' -Encoding ascii
    Set-Content -LiteralPath (Join-Path $root 'outrun-vr-host.exe') -Value 'PREVIOUS_USER_HOST' -Encoding ascii
    $originalDll=(Get-FileHash -LiteralPath (Join-Path $root 'dinput8.dll') -Algorithm SHA256).Hash
    $originalHost=(Get-FileHash -LiteralPath (Join-Path $root 'outrun-vr-host.exe') -Algorithm SHA256).Hash
    $selector=@'
param([string]$Backend,[string]$TestProfile,[string]$VariantId)
$sourceDir=Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'backends/d3d9'
$gameDir=Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item -LiteralPath (Join-Path $sourceDir 'dinput8.dll') -Destination (Join-Path $gameDir 'dinput8.dll') -Force
Copy-Item -LiteralPath (Join-Path $sourceDir 'outrun-vr-host.exe') -Destination (Join-Path $gameDir 'outrun-vr-host.exe') -Force
'@
    $runner=@'
param([string]$TestProfile,[string]$QuestCockpitV2ReleaseParity,
      [string]$QuestCockpitV2,[string]$DinoFitV6)
if($env:OUTRUN_VR_DINO_PBR_TEST -ne '1'){throw 'PBR launch env flag missing'}
if($DinoFitV6 -ne 'ON'){throw 'Dino draw flag missing'}
$gameDir=Split-Path -Parent $MyInvocation.MyCommand.Path
if(!(Test-Path -LiteralPath (Join-Path $gameDir 'Dino246_Cockpit_LHD_v15_PBR.ovc'))){
    throw 'OVC3 sidecar not staged before game launch'
}
Set-Content -LiteralPath (Join-Path $gameDir 'PBR_MODE_TEST_PASS.txt') -Value 'PBR_ONLY' -Encoding ascii
'@
    Set-Content -LiteralPath (Join-Path $payload 'scripts/Select-OutRunVRBackend.ps1') -Value $selector -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $payload 'scripts/Run-OutRunVRTest.ps1') -Value $runner -Encoding UTF8

    # Existing user PBR file must be rejected before backend replacement.
    $destPbr=Join-Path $root 'Dino246_Cockpit_LHD_v15_PBR.ovc'
    Set-Content -LiteralPath $destPbr -Value 'USER_DIFFERENT_PBR' -Encoding ascii
    $rejected=$false
    try {& (Join-Path $root 'QuestCockpit-CopyRun.ps1') -Mode PBR}
    catch {$rejected=($_.Exception.Message -match 'overwrite existing different')}
    if(-not $rejected){throw 'Existing PBR conflict was not rejected before install.'}
    if(Test-Path (Join-Path $root 'QUEST_APK_COPYRUN_ORIGINAL_BACKUP')){
        throw 'Conflict case modified backup before rejecting.'
    }
    Remove-Item -LiteralPath $destPbr

    Copy-Item -LiteralPath $restore -Destination (Join-Path $root 'QuestCockpit-CopyRestore.ps1')
    & (Join-Path $root 'QuestCockpit-CopyRun.ps1') -Mode PBR
    if(-not $? -or !(Test-Path (Join-Path $root 'PBR_MODE_TEST_PASS.txt'))){
        throw 'PBR game launcher mock did not execute in opt-in mode.'
    }
    if($env:OUTRUN_VR_DINO_PBR_TEST){
        throw 'PBR environment flag was not restored after launch.'
    }
    if((Get-Content -LiteralPath $stableModel -Raw).Trim() -ne $original){
        throw 'Stable OVC2 file overwritten by PBR installer.'
    }
    & (Join-Path $root 'QuestCockpit-CopyRestore.ps1')
    if(-not $?){throw 'Restore script failed.'}
    if(Test-Path $destPbr){throw 'Restorer left a newly created PBR sidecar behind.'}
    if((Get-Content -LiteralPath $stableModel -Raw).Trim() -ne $original){
        throw 'Restorer changed stable OVC2 model.'
    }
    if((Get-FileHash -LiteralPath (Join-Path $root 'dinput8.dll') -Algorithm SHA256).Hash -ne $originalDll -or
       (Get-FileHash -LiteralPath (Join-Path $root 'outrun-vr-host.exe') -Algorithm SHA256).Hash -ne $originalHost){
        throw 'Restorer failed to restore original user DLL/host.'
    }
    Write-Host 'DINO_PBR_SYNTHETIC_INSTALL_OPTIN_STABLE_OVC2_AND_RESTORE_PASS'
    Write-Host 'DINO_PBR_POWERSHELL_PARSE_VERIFYONLY_SOURCE_AND_SIDECAR_GATES_PASS'
} finally {
    if(Test-Path $root){Remove-Item -LiteralPath $root -Recurse -Force}
}
