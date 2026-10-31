@echo off
setlocal
title OutRun R26 VR - Restore Pre-Test Files
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESTORE_PREVIOUS.ps1"
if errorlevel 1 echo ERROR: Recovery incomplete. Check errors above.
pause
