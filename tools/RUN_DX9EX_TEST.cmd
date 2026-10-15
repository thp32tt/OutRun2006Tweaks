@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9ExFocusTest.ps1"
if errorlevel 1 (
  echo.
  echo DX9Ex test launcher failed. See the message above.
)
echo.
pause
