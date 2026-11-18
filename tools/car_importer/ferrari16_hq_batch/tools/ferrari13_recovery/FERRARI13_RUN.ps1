param([ValidateSet('Start','Verify')][string]$Mode='Start')
$ErrorActionPreference='Stop'
$game=$PSScriptRoot
$payload=Join-Path $game 'FERRARI13_PAYLOAD'
$installer=Join-Path $payload 'INSTALL_FERRARI13.ps1'
$manifestPath=Join-Path $payload 'manifest.json'
$exe=Join-Path $game 'OR2006C2C.EXE'
$diag=Join-Path $game 'FERRARI13_DIAG'
function Hash-Lower([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
function Installed {
    $m=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
    if($m.Schema -ne 1 -or $m.CarCount -ne 13 -or $m.Status -ne 'STATIC_QA_PASS_NOT_QUEST3_TESTED' -or @($m.Files).Count -ne 30){throw 'Invalid Ferrari13 manifest'}
    foreach($f in @($m.Files)){
        $rel=[string]$f.Target
        if($rel -match '(^[\\/]|(^|[\\/])\.\.([\\/]|$)|:|[^\w./\\-])'){throw 'Unsafe manifest path'}
        $dst=Join-Path $game $rel
        if($f.Mode -eq 'missing-only' -and (Test-Path -LiteralPath $dst -PathType Leaf)){continue}
        if(!(Test-Path -LiteralPath $dst -PathType Leaf)){return $false}
        if((Get-Item -LiteralPath $dst).Length -ne [long]$f.Bytes){return $false}
        if((Hash-Lower $dst) -ne ([string]$f.Sha256).ToLowerInvariant()){return $false}
    }
    return $true
}
if(!(Test-Path -LiteralPath $exe -PathType Leaf)){throw 'OR2006C2C.EXE not found. Extract ZIP into your existing game directory.'}
if(!(Test-Path -LiteralPath $installer -PathType Leaf) -or !(Test-Path -LiteralPath $manifestPath -PathType Leaf)){throw 'FERRARI13_PAYLOAD missing. Re-extract entire ZIP.'}
if($Mode -eq 'Verify'){
    & $installer -VerifyOnly
    if(Installed){Write-Host 'PASS: 13 bodies, 13 gauges, host and DLL installed.'}
    else{Write-Host 'PASS: ZIP source verified; files are not yet installed. START will install them.'}
    return
}
$running=@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue)
if($running.Count){throw 'Close game and VR host before launching.'}
New-Item -ItemType Directory -Path $diag -Force|Out-Null
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$log=Join-Path $diag ('FERRARI13_RUN_'+$stamp+'.log')
"START UTC=$((Get-Date).ToUniversalTime().ToString('o'))" |Set-Content -LiteralPath $log -Encoding UTF8
try{
    & $installer -VerifyOnly
    if(!(Installed)){
        Write-Host 'Installing and backing up 13 exact car models and matched runtime...'
        & $installer -GameDir $game
        Add-Content -LiteralPath $log -Value 'InstalledWithBackup=true'
    }else{Add-Content -LiteralPath $log -Value 'InstalledWithBackup=false'}
    if(!(Installed)){throw 'Post-install hash verification failed'}
    Add-Content -LiteralPath $log -Value ('DllSha256='+(Hash-Lower (Join-Path $game 'dinput8.dll')))
    Add-Content -LiteralPath $log -Value ('HostSha256='+(Hash-Lower (Join-Path $game 'outrun-vr-host.exe')))
    $args=@(
        '-VR.Enabled=true',
        '-VR.Stereo=true',
        '-VR.AutoLaunchHost=true',
        '-VR.QuestCockpitV2Enabled=true',
        '-VR.QuestCockpitV2FullCar=true',
        '-VR.QuestCockpitV2HideDriver=true',
        '-VR.QuestCockpitV2RawB0Camera=false',
        '-VR.QuestCockpitV2NativeSeatProfile=true',
        '-VR.QuestCockpitV2ApkNativeCamera=true',
        '-VR.QuestCockpitV2GlassReflectionOff=true',
        '-VR.QuestCockpitV2OccupantCorrection=true',
        '-VR.QuestCockpitV2OccupantLod0=false',
        '-VR.QuestCockpitV2F0RenderScope=false',
        '-VR.F50ExternalModel=true',
        '-VR.ExternalFerrariTest=true',
        '-VR.F50ExternalLift=0.22',
        '-VR.F50ExternalStabilize=true',
        '-VR.PreferD3D9Ex=false',
        '-VR.DirectGpuOnly=false',
        '-VR.AutoRenderResolution=false',
        '-VR.FollowGameResolution=true',
        '-VR.FrameCadenceMode=0',
        '-VR.DisableDesktopDuplication=false',
        '-VR.CockpitFrameProbe=true',
        '-VR.Telemetry=false',
        '-FileLogging=true'
    )
    Add-Content -LiteralPath $log -Value ('Arguments='+($args -join ' '))
    $oldLaunch=$env:OUTRUN_VR_LAUNCH
    $oldLog=$env:OUTRUN_VR_FILE_LOG
    $oldPixelProbe=$env:OUTRUN_VR_R23_PIXEL_PROBE
    try{
        $env:OUTRUN_VR_LAUNCH='1'
        $env:OUTRUN_VR_FILE_LOG='1'
        $env:OUTRUN_VR_R23_PIXEL_PROBE='1'
        $proc=Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $game -PassThru -ErrorAction Stop
    }finally{
        $env:OUTRUN_VR_LAUNCH=$oldLaunch
        $env:OUTRUN_VR_FILE_LOG=$oldLog
        $env:OUTRUN_VR_R23_PIXEL_PROBE=$oldPixelProbe
    }
    Add-Content -LiteralPath $log -Value ('GamePid='+$proc.Id)
    Write-Host ('Launched RECOVERY game PID='+$proc.Id+', file log ON, DirectGpuOnly OFF.')
    Write-Host 'If white screen persists, run COLLECT-FERRARI13-LOGS.cmd in another window. Do not wait for game to exit.'
    Write-Host 'Start an actual driving stage and select cockpit view (camera mode 1).'
    $proc.WaitForExit()
    Add-Content -LiteralPath $log -Value ('GameExitCode='+$proc.ExitCode)
    Add-Content -LiteralPath $log -Value ('ExitUTC='+((Get-Date).ToUniversalTime().ToString('o')))
    & (Join-Path $game 'FERRARI13_COLLECT.ps1')
}catch{
    $msg=$_.Exception.Message
    Add-Content -LiteralPath $log -Value ('ERROR='+$msg) -ErrorAction SilentlyContinue
    Write-Host ('ERROR: '+$msg)
    try { & (Join-Path $game 'FERRARI13_COLLECT.ps1') } catch {}
    throw
}