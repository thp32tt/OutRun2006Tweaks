@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9Ex-White-Test.ps1"
echo.
pause
