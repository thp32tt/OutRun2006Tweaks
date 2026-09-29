@echo off
setlocal
cd /d "%~dp0"
title OutRun 2006 VR R71 - HUD / Lens Flare Test

cls
echo ============================================================
echo  OUTRUN 2006 VR R71 - HUD / LENS FLARE EVENING TEST
echo ============================================================
echo.
echo  Run this file only.
echo  Select the recommended full test in the window.
echo  When the game exits, logs are collected and analyzed automatically.
echo  Upload only the newest OutRun2_VR_ANALYZE_*.zip.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OutRunVR-Test-Selector.ps1"
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo TEST LAUNCHER FAILED.
echo Upload any newly-created OutRun2_VR_ANALYZE_*.zip,
echo or a screenshot of this window.
pause
exit /b 1
