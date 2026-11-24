@echo off
setlocal
cd /d "%~dp0"

rem Never launch a global mod test from a working v0.03 install.
if not exist "%~dp0.ferrari16-isolated.json" (
 echo [EXT16] Refusing to launch outside a prepared isolated test copy.
 exit /b 87
)
if not exist "%~dp0OR2006C2C.exe" (
 echo [EXT16] Isolated game EXE missing.
 exit /b 87
)

if /I "%~1"=="2d" goto MODE_2D
if /I "%~1"=="vr" goto MODE_VR

echo.
echo OutRun 2006 launch mode
echo -----------------------
echo [1] 2D + FFB
echo [2] VR + FFB
echo.
choice /C 12 /N /M "Select 1 or 2: "
rem CHOICE returns 0 on cancel, 255 on error; neither is a launch request.
if errorlevel 3 exit /b 89
if errorlevel 2 goto MODE_VR
if errorlevel 1 goto MODE_2D
exit /b 89

:MODE_2D
rem The release dinput8.dll contains both the normal Tweaks/FFB code and VR.
rem Direct 2D explicitly disables only VR hooks; wheel FFB stays loaded.
rem A globally named taskkill would terminate even the working v0.03 host.
rem Fail closed instead; close any existing host manually before testing.
call :CHECK_HOST
if errorlevel 89 exit /b 89
if errorlevel 88 exit /b 88
if errorlevel 1 exit /b 89
set "OUTRUN_VR_LAUNCH=0"
set "OUTRUN_VR_FORCE_DISABLED=1"
set "OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=0"
set "OUTRUN_VR_EXTERNAL_PBR_STEREO_TEST=0"
set "OUTRUN_VR_FILE_LOG=0"
start "" "%~dp0OR2006C2C.exe"
exit /b 0

:MODE_VR
rem Ferrari16 isolated PBR/normal-map diagnostic, not a release launcher.
rem Ferrari16 private diagnostic on unmodified v0.03 VR launch settings.
rem No PowerShell script is required: all launch-only VR settings are passed here.
rem A globally named taskkill would terminate even the working v0.03 host.
rem Fail closed instead; close any existing host manually before testing.
call :CHECK_HOST
if errorlevel 89 exit /b 89
if errorlevel 88 exit /b 88
if errorlevel 1 exit /b 89
set "OUTRUN_VR_LAUNCH=1"
set "OUTRUN_VR_FORCE_DISABLED=0"
set "OUTRUN_VR_R23_PIXEL_PROBE=0"
set "OUTRUN_VR_FILE_LOG=1"
rem PBR-only diagnostic: fixed-function probe OFF, independent PBR
rem admission ON. All runtime and R7 dual-eye receipts still fail closed.
rem Neither flag is enabled by the protected v0.03 release launcher.
set "OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=0"
set "OUTRUN_VR_EXTERNAL_PBR_STEREO_TEST=1"

rem Isolated sixteen-car driver-eye A/B only; never install into working v0.03.
rem Match the proven diagnostic startup order: prepare the OpenXR host before the
rem game process, and keep the host hidden so it cannot steal foreground focus.
rem If PowerShell host prewarm is unavailable, the DLL AutoLaunchHost path below
rem remains a fallback and uses the same transport policy.
set "OUTRUN_VR_DIRECT_TRANSPORT=1"
set "OUTRUN_VR_DIRECT_ONLY=1"
set "OUTRUN_VR_DISABLE_DESKTOP_DUPLICATION=0"
set "OUTRUN_VR_TARGET_REFRESH_HZ=0"
rem Pin physical A/B host to runtime-recommended scale (v0.03 default).
set "OUTRUN_VR_RENDER_SCALE=1.0"
set "OUTRUN_VR_CADENCE_MODE=1"
set "OUTRUN_VR_CADENCE_TARGET_HZ=0"
set "OUTRUN_VR_CADENCE_MAX_HZ=120"
set "OUTRUN_VR_CADENCE_TIMEOUT_MS=35"
set "OUTRUN_VR_HOST=%~dp0outrun-vr-host.exe"
set "OUTRUN_VR_ROOT=%~dp0"
if exist "%OUTRUN_VR_HOST%" (
 powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -Command "Start-Process -FilePath $env:OUTRUN_VR_HOST -WorkingDirectory $env:OUTRUN_VR_ROOT -WindowStyle Hidden" >nul 2>&1
)

start "" "%~dp0OR2006C2C.exe" ^
 -VR.Enabled=true ^
 -VR.HmdlessDebugMode=0 ^
 -VR.Stereo=true ^
 -VR.AutoLaunchHost=true ^
 -FramerateLimit=0 ^
 -FramerateFastLoad=0 ^
 -FramerateInterpolation=true ^
 -FramerateUnlockExperimental=true ^
 -VR.FrameCadenceMode=1 ^
 -VR.FrameCadenceTargetHz=0 ^
 -VR.DisableDesktopVsync=true ^
 -SkyGlowFactor=0 ^
 -VR.PreferD3D9Ex=true ^
 -VR.DirectGpuOnly=true ^
 -VR.DisableDesktopDuplication=false ^
 -Graphics.ReflectionUpdateRate=0.25 ^
 -Graphics.TransparencySupersampling=false ^
 -VR.TransparencySupersampling=false ^
 -VR.Telemetry=false ^
 -VR.RivalDx11NativeRoute=false ^
 -VR.AutoRenderResolution=false ^
 -VR.RenderWidth=2496 ^
 -VR.RenderHeight=2688 ^
 -VR.FollowGameResolution=false ^
 -VR.MirrorFitDesktop=true ^
 -VR.MirrorPreserveAspect=true ^
 -VR.UnifiedEyeMenuSource=false ^
 -VR.AntiAliasing=2 ^
 -VR.Hud1080pReference=true ^
 -VR.HudResponsiveLayout=true ^
 -VR.HudScale=0.55 ^
 -VR.MenuScale=0.75 ^
 -VR.CullingUnionFov=true ^
 -VR.CullingUnionMarginDegrees=8.0 ^
 -VR.QuestCockpitV2Enabled=true ^
 -VR.QuestCockpitV2FullCar=true ^
 -VR.QuestCockpitV2HideDriver=true ^
 -VR.QuestCockpitV2RawB0Camera=false ^
 -VR.QuestCockpitV2NativeSeatProfile=true ^
 -VR.QuestCockpitV2ApkNativeCamera=true ^
 -VR.QuestCockpitV2GlassEnabled=false ^
 -VR.QuestCockpitV2GlassHidden=false ^
 -VR.QuestCockpitV2GlassReflectionOff=true ^
 -VR.QuestCockpitV2SkyProbe=false ^
 -VR.QuestCockpitV2OccupantCorrection=true ^
 -VR.QuestCockpitV2OccupantLod0=false ^
 -VR.QuestCockpitV2F0RenderScope=true ^
 -VR.CockpitFrameProbe=false ^
 -HudInspector=false ^
 -VR.FileLogging=true ^
 -VR.ExternalFerrariTest=true ^
 -VR.ExternalFerrariTestCarId=-1 ^
 -VR.F50ExternalModel=false ^
 -VR.ExternalFerrariNativeCallbackReplacement=true ^
 -VR.F50ExternalStabilize=false ^
 -VR.ExternalFerrariDiag=true
exit /b 0

:CHECK_HOST
rem FOR /F consumes CSV image names plus an explicit successful-scan marker.
rem The marker is emitted only if TASKLIST succeeds; a failed query must
rem never be treated as proof that the v0.03 host is absent.
set "EXT16_HOST_SCAN_OK="
set "EXT16_HOST_FOUND="
for /f "tokens=1 delims=," %%P in ('tasklist /FI "IMAGENAME eq outrun-vr-host.exe" /FO CSV /NH 2^>nul ^&^& echo EXT16_TASKLIST_OK') do (
 if /I "%%~P"=="outrun-vr-host.exe" set "EXT16_HOST_FOUND=1"
 if "%%~P"=="EXT16_TASKLIST_OK" set "EXT16_HOST_SCAN_OK=1"
)
if not defined EXT16_HOST_SCAN_OK (
 echo [EXT16] Cannot verify VR host absence. Refusing isolated launch.
 exit /b 89
)
if defined EXT16_HOST_FOUND (
 echo [EXT16] Another VR host is running. Close it before isolated testing.
 exit /b 88
)
exit /b 0
