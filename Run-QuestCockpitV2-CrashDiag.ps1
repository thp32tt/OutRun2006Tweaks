param(
    [ValidateRange(1,6)][int]$Test = 1
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'
if(!(Test-Path -LiteralPath $runner)){throw 'Run-OutRunVRTest.ps1 is missing: extract the complete test build'}
if(!(Test-Path -LiteralPath (Join-Path $root 'OR2006C2C.EXE'))){throw 'Game EXE missing'}
$dumpDir=Join-Path $root 'VR_CRASH_DUMPS'
New-Item -ItemType Directory -Force -Path $dumpDir | Out-Null
$key='HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps\OR2006C2C.exe'
$existed=Test-Path -LiteralPath $key
$old=@{}
$names=@('DumpFolder','DumpType','DumpCount')
if($existed){
    $handle=Get-Item -LiteralPath $key
    foreach($name in $names){
        if(@($handle.GetValueNames()) -contains $name){
            $old[$name]=@{Exists=$true;Value=$handle.GetValue($name);Kind=$handle.GetValueKind($name)}
        }else{$old[$name]=@{Exists=$false}}
    }
}
$originalDeviceDiag=$env:OUTRUN_VR_COCKPIT_DEVICE_DIAG
$originalLog=$env:OUTRUN_VR_FILE_LOG
$originalLaunch=$env:OUTRUN_VR_LAUNCH
$exitCode=1
$start=Get-Date
try{
    if(-not $existed){New-Item -Path $key -Force | Out-Null}
    # Temporary per-user Windows Error Reporting LocalDumps setting.
    # Restore pre-existing registry data in finally, even if the game exits abnormally.
    New-ItemProperty -LiteralPath $key -Name DumpFolder -Value $dumpDir -PropertyType ExpandString -Force | Out-Null
    New-ItemProperty -LiteralPath $key -Name DumpType -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -LiteralPath $key -Name DumpCount -Value 2 -PropertyType DWord -Force | Out-Null
    $env:OUTRUN_VR_FILE_LOG='1'
    $env:OUTRUN_VR_COCKPIT_DEVICE_DIAG='1'
    $env:OUTRUN_VR_LAUNCH='1'
    Write-Host "Quest cockpit test mode=$Test. WER mini-dump directory: $dumpDir"
    Write-Host "Release marker present: $(Test-Path -LiteralPath (Join-Path $root 'VR_RELEASE_VERSION.txt'))"
    $launchArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,
            '-TestProfile','CORRECTNESS','-QuestCockpitV2ReleaseParity','ON',
            '-QuestCockpitV2Diagnostics','ON',
            '-QuestCockpitV2','OFF')
    switch($Test){
      1 {Write-Host 'CONTROL: No cockpit hooks; diagnostic file logging ON'}
      2 {$launchArgs+=@('-QuestCockpitV2FrameOnly','ON'); Write-Host 'FRAME ONLY: original native-hook observer'}
      3 {$launchArgs[($launchArgs.Count-1)]='ON'; Write-Host 'V2 core: no F0/LOD0'}
      4 {$launchArgs[($launchArgs.Count-1)]='ON';$launchArgs+=@('-QuestCockpitV2F0','ON');Write-Host 'V2 + F0 (only after 3 passes)'}
      5 {$launchArgs[($launchArgs.Count-1)]='ON';$launchArgs+=@('-QuestCockpitV2Lod0','ON');Write-Host 'V2 + LOD0 (only after 3 passes)'}
      6 {$launchArgs+=@('-QuestCockpitV2DeviceMode','CLASSIC');Write-Host 'CLASSIC A/B: no cockpit + original D3D9 device (no Ex promotion)'}
    }
    & powershell.exe @launchArgs
    $exitCode=$LASTEXITCODE
}
finally{
    $env:OUTRUN_VR_LAUNCH=$originalLaunch
    $env:OUTRUN_VR_FILE_LOG=$originalLog
    $env:OUTRUN_VR_COCKPIT_DEVICE_DIAG=$originalDeviceDiag
    try{
        if(!$existed){Remove-Item -LiteralPath $key -Force -ErrorAction Stop}
        else{
            foreach($name in $names){
                $entry=$old[$name]
                if($entry.Exists){
                    New-ItemProperty -LiteralPath $key -Name $name -Value $entry.Value -PropertyType $entry.Kind.ToString() -Force | Out-Null
                }else{
                    Remove-ItemProperty -LiteralPath $key -Name $name -ErrorAction SilentlyContinue
                }
            }
        }
    }catch{Write-Warning "WER registry restore requires manual check: $($_.Exception.Message)"}
}
$dumps=@(Get-ChildItem -LiteralPath $dumpDir -Filter '*.dmp' -File -ErrorAction SilentlyContinue |
         Where-Object { $_.LastWriteTime -ge $start.AddSeconds(-3) } |
         Sort-Object LastWriteTime -Descending)
if($dumps.Count){
    Write-Host "CRASH DUMP: $($dumps[0].FullName)"
    Write-Host "Send the newest .dmp (if manageable) AND the session analysis ZIP."
}else{Write-Host 'No Windows Error Reporting dump created for this run.'}
Write-Host "Exit code: $exitCode"
exit $exitCode
