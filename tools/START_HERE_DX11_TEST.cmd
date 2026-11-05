@echo off
setlocal EnableExtensions DisableDelayedExpansion
title OutRun 2006 - DX11 branch user VR test
set "launchResult=0"
pushd "%~dp0" 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot open the extracted game directory.
  pause
  exit /b 2
)
echo ============================================================
echo OutRun 2006 VR - DX11 development branch compatibility test
echo ============================================================
echo Extract ALL archive files into the original game's folder.
echo NEVER start outrun-vr-host.exe directly; it is a helper.
echo.
if not exist "OR2006C2C.EXE" (
  echo [ERROR] OR2006C2C.EXE not found. Copy the full package into the game folder.
  set "launchResult=2"
  goto :finish
)
if not exist "dinput8.dll" (
  echo [ERROR] Missing Win32 game hook dinput8.dll.
  set "launchResult=3"
  goto :finish
)
if not exist "outrun-vr-host.exe" (
  echo [ERROR] Missing x64 OpenXR host. Do not run a binary-only artifact.
  set "launchResult=3"
  goto :finish
)
if not exist "OutRun2006Tweaks.ini" (
  echo [ERROR] Missing OutRun2006Tweaks.ini.
  set "launchResult=3"
  goto :finish
)
if not exist "Run-DX9ExFocusTest.ps1" (
  echo [ERROR] Missing Run-DX9ExFocusTest.ps1.
  set "launchResult=3"
  goto :finish
)
if not exist "DX9EX_VARIANT.txt" (
  echo [ERROR] Missing DX9EX_VARIANT.txt.
  set "launchResult=3"
  goto :finish
)
where powershell.exe >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Windows PowerShell was not found.
  set "launchResult=4"
  goto :finish
)
echo [RUN] Launch game + VR helper through the package runner.
echo [INFO] This is the DX11 branch's safe fallback test, NOT proof of native DX11 stereo.
set "OUTRUN_VR_DX11_CENSUS=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\Run-DX9ExFocusTest.ps1"
if errorlevel 1 (
  echo [ERROR] Test runner failed. Preserve DX9EX_LOGS and console output.
  set "launchResult=5"
  goto :finish
)
echo [OK] Test session ended; review DX9EX_LOGS.
:finish
if not "%launchResult%"=="0" echo [FAILED] Launch status %launchResult%.
echo Press any key to close this window.
popd
pause >nul
exit /b %launchResult%
