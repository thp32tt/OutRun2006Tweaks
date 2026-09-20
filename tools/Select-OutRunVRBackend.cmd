@echo off
setlocal
if "%~1"=="" (
  echo Usage: Select-OutRunVRBackend.cmd 2d^|d3d9^|dxvk-safe^|dxvk^|dx12
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Select-OutRunVRBackend.ps1" "%~1"
exit /b %ERRORLEVEL%
