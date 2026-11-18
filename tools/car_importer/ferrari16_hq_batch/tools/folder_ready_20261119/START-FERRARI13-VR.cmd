@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0FERRARI13_RUN.ps1" -Mode Start
if errorlevel 1 echo Ferrari13 launch error. Please run COLLECT-FERRARI13-LOGS.cmd
echo.
echo Ferrari13 session ended. Press a key to close.
pause >nul