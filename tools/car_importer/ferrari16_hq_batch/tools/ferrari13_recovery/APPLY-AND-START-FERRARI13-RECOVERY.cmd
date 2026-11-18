@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0APPLY-FERRARI13-RECOVERY.ps1"
if errorlevel 1 (echo RECOVERY INSTALL FAILED. Read the error above. & pause & exit /b 1)
call "%~dp0START-FERRARI13-VR.cmd"
