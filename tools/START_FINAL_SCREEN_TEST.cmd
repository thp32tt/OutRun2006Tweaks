@echo off
setlocal EnableExtensions DisableDelayedExpansion
title OutRun 2006 VR - R26+HUD Final Screen Test
pushd "%~dp0" 2>nul
if errorlevel 1 (
 echo [ERROR] Cannot open package directory.
 pause
 exit /b 2
)
set "result=0"
echo === R26+HUD FINAL SCREEN TEST: %CD% ===
for %%F in ("OR2006C2C.EXE" "dinput8.dll" "outrun-vr-host.exe" "OutRun2006Tweaks.ini" "Run-FinalScreenTest.ps1" "DX9EX_VARIANT.txt") do (
 if not exist "%%~F" (
  echo [ERROR] Missing %%~F
  set "result=3"
  goto :finish
 )
)
where powershell.exe >nul 2>&1
if errorlevel 1 (
 echo [ERROR] Windows PowerShell not found.
 set "result=4"
 goto :finish
)
echo [RUN] Starting game using bundled x86 dinput8.dll and x64 OpenXR host.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\Run-FinalScreenTest.ps1"
set "result=%errorlevel%"
:finish
if not "%result%"=="0" (
 echo [FAILED] Exit code %result%.
 if exist "OUTRUNVR_LAUNCH_ERROR.txt" type "OUTRUNVR_LAUNCH_ERROR.txt"
 echo For diagnosis, keep DX9EX_LAUNCH_HEALTH.txt and DX9EX_LOGS folder.
) else (
 echo [OK] Game exited and host health recorded.
)
popd
pause
exit /b %result%
