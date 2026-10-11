@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OutRunVR-GPU-Lab.ps1"
if errorlevel 1 pause
