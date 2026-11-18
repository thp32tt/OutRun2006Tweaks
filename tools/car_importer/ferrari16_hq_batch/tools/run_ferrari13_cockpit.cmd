@echo off
setlocal
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_FERRARI13_COCKPIT.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_FERRARI13_COCKPIT.ps1" -GameDir "%~1"
)
if errorlevel 1 (
  echo.
  echo Ferrari13 cockpit launch failed. Read the error above.
  pause
  exit /b 1
)
exit /b 0
