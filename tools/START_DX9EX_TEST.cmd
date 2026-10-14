@echo off
setlocal EnableExtensions DisableDelayedExpansion
title OutRun 2006 VR DX9Ex direct launcher
set "result=0"
pushd "%~dp0" 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot open extracted folder.
  pause
  exit /b 2
)
echo === DX9Ex CURRENT_FOCUS CORRECTNESS ===
echo Folder: "%CD%"
if not exist "OR2006C2C.EXE" (
 echo [ERROR] OR2006C2C.EXE not found. Extract ZIP directly into game folder.
 set "result=2"
 goto :finish
)
if not exist "backends\d3d9\dinput8.dll" (
 echo [ERROR] Missing backends\d3d9\dinput8.dll.
 set "result=3"
 goto :finish
)
if not exist "backends\d3d9\outrun-vr-host.exe" (
 echo [ERROR] Missing backends\d3d9\outrun-vr-host.exe.
 set "result=3"
 goto :finish
)
if not exist "OutRun2006Tweaks.ini" (
 echo [ERROR] Missing OutRun2006Tweaks.ini.
 set "result=3"
 goto :finish
)
if not exist "Select-OutRunVRBackend.ps1" (
 echo [ERROR] Missing Select-OutRunVRBackend.ps1.
 set "result=3"
 goto :finish
)
if not exist "Run-OutRunVRTest.ps1" (
 echo [ERROR] Missing Run-OutRunVRTest.ps1.
 set "result=3"
 goto :finish
)
where powershell.exe >nul 2>&1
if errorlevel 1 (
 echo [ERROR] Windows PowerShell unavailable.
 set "result=4"
 goto :finish
)
echo [1/2] Install DX9Ex backend...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\Select-OutRunVRBackend.ps1" -Backend d3d9 -TestProfile CORRECTNESS -VariantId CURRENT_FOCUS
if errorlevel 1 (
 echo [ERROR] Backend installation failed.
 set "result=5"
 goto :finish
)
echo [2/2] Run game and inspect OpenXR host...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS
if errorlevel 1 (
 echo [ERROR] Launch/host check failed.
 set "result=6"
 goto :finish
)
echo [OK] Session complete.
:finish
if not "%result%"=="0" (
 echo [FAILED] Exit status %result%
 if exist "OUTRUNVR_LAUNCH_ERROR.txt" type "OUTRUNVR_LAUNCH_ERROR.txt"
 echo See logs or collected OutRun2_VR_ANALYZE_*.zip.
)
echo Press any key to exit...
popd
pause >nul
exit /b %result%
