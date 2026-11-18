param(
    [string]$GameDir = '',
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$game = if ([string]::IsNullOrWhiteSpace($GameDir)) { $PSScriptRoot } else { (Resolve-Path -LiteralPath $GameDir).Path }
if ([string]::IsNullOrWhiteSpace($game) -or !(Test-Path -LiteralPath $game -PathType Container)) {
    throw 'Game directory not found. Extract the HOTFIX into the folder containing OR2006C2C.EXE, or pass -GameDir.'
}
$exe = Join-Path $game 'OR2006C2C.EXE'
$dll = Join-Path $game 'dinput8.dll'
$hostExe = Join-Path $game 'outrun-vr-host.exe'
$expectedDll = '313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e'
$expectedHost = 'e12a136cba5110216180b68ee2c20cadac1e0fe365bc0a58c4d42003360b5e40'
$models = @(
    'ExternalCars\car_id_00.ovc', 'ExternalCars\car_id_01.ovc',
    'F50_External_Test.ovc', 'ExternalCars\car_id_03.ovc',
    'ExternalCars\car_id_04.ovc', 'ExternalCars\car_id_06.ovc',
    'ExternalCars\288gto.ovc', 'ExternalCars\car_id_09.ovc',
    'ExternalCars\car_id_10.ovc', 'ExternalCars\f40.ovc',
    'ExternalCars\car_id_12.ovc', 'ExternalCars\car_id_13.ovc',
    'ExternalCars\car_id_14.ovc'
)
$dashIds = @('00','01','02','03','04','06','07','09','10','11','12','13','14')
foreach ($path in @($exe, $dll, $hostExe)) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required file missing: $path. Run INSTALL_FERRARI13.cmd first; keep your own original game executable."
    }
}
$actualDll = (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash.ToLowerInvariant()
$actualHost = (Get-FileHash -LiteralPath $hostExe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualDll -ne $expectedDll) {
    throw "Wrong installed dinput8.dll. Expected integrated Ferrari13 V4: $expectedDll; actual: $actualDll. Reinstall the 13-car private package or restore your previous VR build."
}
if ($actualHost -ne $expectedHost) {
    throw "Wrong installed outrun-vr-host.exe. Expected matched Quest V2 host: $expectedHost; actual: $actualHost. Use host and DLL from the same Ferrari13 package."
}
$missing = @()
foreach ($name in $models) {
    if (!(Test-Path -LiteralPath (Join-Path $game $name) -PathType Leaf)) { $missing += $name }
}
foreach ($id in $dashIds) {
    $name = "ExternalCars\Dashboard\car_id_$id.ovc"
    if (!(Test-Path -LiteralPath (Join-Path $game $name) -PathType Leaf)) { $missing += $name }
}
if ($missing.Count -gt 0) {
    throw ("Missing Ferrari13 OVC files: " + ($missing -join ', ') + ". Install the 13-car package before this launcher.")
}
Write-Host 'PASS: game EXE present; correct integrated V4 DLL, Quest V2 host, 13 bodies and 13 overlays.'
Write-Host 'The original INSTALL_FERRARI13.cmd only installed files. This launcher STARTS QuestCockpitV2.'
if ($VerifyOnly) {
    Write-Host 'PASS: Launcher prerequisites verified. No game started; INI was not modified.'
    return
}
$running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
})
if ($running.Count -gt 0) { throw 'Exit OutRun 2006 and the VR host before launching.' }
$args = @(
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
    '-VR.CockpitFrameProbe=false',
    '-VR.Telemetry=false',
    '-FileLogging=false'
)
$oldLaunch = $env:OUTRUN_VR_LAUNCH
$oldFileLog = $env:OUTRUN_VR_FILE_LOG
try {
    # The release DllMain gate requires this environment variable.
    # The CLI flags override QuestCockpitV2Enabled=false in default INI.
    $env:OUTRUN_VR_LAUNCH = '1'
    $env:OUTRUN_VR_FILE_LOG = '0'
    $process = Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $game -PassThru -ErrorAction Stop
    Write-Host ("Launched PID={0}: VR Enabled/Stereo/QuestCockpitV2/external Ferrari all ON." -f $process.Id)
    Write-Host 'Enter a driving stage and switch to the in-game cockpit camera (mode 1).'
} finally {
    $env:OUTRUN_VR_LAUNCH = $oldLaunch
    $env:OUTRUN_VR_FILE_LOG = $oldFileLog
}
