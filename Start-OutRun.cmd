@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="2d" goto MODE_2D
if /I "%~1"=="vr" goto MODE_VR

echo.
echo OutRun 2006 launch mode
echo -----------------------
echo [1] 2D + FFB
echo [2] VR + FFB
echo.
choice /C 12 /N /M "Select 1 or 2: "
if errorlevel 2 goto MODE_VR
goto MODE_2D

:MODE_2D
rem The release dinput8.dll contains both the normal Tweaks/FFB code and VR.
rem Direct 2D explicitly disables only VR hooks; wheel FFB stays loaded.
taskkill /IM outrun-vr-host.exe /F >nul 2>&1
set "OUTRUN_VR_LAUNCH=0"
set "OUTRUN_VR_FORCE_DISABLED=1"
set "OUTRUN_VR_FILE_LOG=0"
start "" "%~dp0OR2006C2C.exe"
exit /b 0

:MODE_VR
rem v0.02 cockpit release: validated DX9Ex profile + Quest cockpit/F0/seat baseline.
rem No PowerShell script is required: all launch-only VR settings are passed here.
taskkill /IM outrun-vr-host.exe /F >nul 2>&1
set "OUTRUN_VR_LAUNCH=1"
set "OUTRUN_VR_FORCE_DISABLED=0"
set "OUTRUN_VR_R23_PIXEL_PROBE=0"
set "OUTRUN_VR_FILE_LOG=0"

start "" "%~dp0OR2006C2C.exe" ^
 -VR.Enabled=true ^
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
 -VR.AutoRenderResolution=true ^
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
 -VR.QuestCockpitV2PassengerVisible=true ^
 -VR.QuestCockpitV2SkyProbe=false ^
 -VR.QuestCockpitV2OccupantCorrection=true ^
 -VR.QuestCockpitV2OccupantLod0=false ^
 -VR.QuestCockpitV2F0RenderScope=true ^
 -VR.QuestCockpitV2SeatBack=-0.08 ^
 -VR.QuestCockpitV2SeatDown=0.8 ^
 -VR.QuestCockpitV2SeatRight=0.0 ^
 -VR.CockpitFrameProbe=false ^
 -HudInspector=false ^
 -VR.FileLogging=false
exit /b 0
