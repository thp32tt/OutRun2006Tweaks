@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OutRunVR-Visual-Isolation-Selector.ps1"
if errorlevel 1 pause
