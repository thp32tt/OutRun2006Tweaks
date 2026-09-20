@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9Ex-Range16-Test.ps1"
echo.
pause
