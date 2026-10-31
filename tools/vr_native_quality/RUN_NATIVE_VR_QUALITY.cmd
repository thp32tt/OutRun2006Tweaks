@echo off
setlocal
title OutRun 2006 - Native D3D9Ex High Quality VR Diagnostic
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-VRNativeD3D9Ex.ps1" %*
if errorlevel 1 (
  echo.
  echo Native VR test failed. The wrapper restore step should have run.
  echo Review errors and VR_NATIVE_D3D9_BACKUP before another test.
)
echo.
pause
