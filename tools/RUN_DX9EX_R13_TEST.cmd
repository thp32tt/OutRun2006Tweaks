@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9Ex-R13-Test.ps1"
echo.
pause
