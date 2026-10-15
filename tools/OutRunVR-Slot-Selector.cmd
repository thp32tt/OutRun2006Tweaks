@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OutRunVR-Slot-Selector.ps1"
if errorlevel 1 pause
