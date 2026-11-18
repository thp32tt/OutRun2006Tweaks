@echo off
setlocal
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_FERRARI13_COCKPIT.ps1" -VerifyOnly
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_FERRARI13_COCKPIT.ps1" -GameDir "%~1" -VerifyOnly
)
pause
exit /b %errorlevel%
