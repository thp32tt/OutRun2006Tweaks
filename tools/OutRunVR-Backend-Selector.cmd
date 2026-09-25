@echo off
setlocal
if exist "%~dp0OutRunVR-Slot-Selector.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0OutRunVR-Slot-Selector.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0OutRunVR-Backend-Selector.ps1"
)
