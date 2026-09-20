@echo off
setlocal
if "%~1"=="" (
  echo Usage: Select-OutRunVRBackend.cmd d3d9^|dxvk^|dx12
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Select-OutRunVRBackend.ps1" "%~1"
exit /b %ERRORLEVEL%
