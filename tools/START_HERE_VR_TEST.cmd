@echo off
setlocal
cd /d "%~dp0"
title OutRun 2006 VR Tonight Test

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OutRunVR-Test-Selector.ps1"
set RC=%ERRORLEVEL%
if "%RC%"=="2" goto :cancelled
if not "%RC%"=="0" goto :failed

echo.
echo ============================================================
echo  VR TEST COMPLETE
echo  Upload the newest OutRun2_VR_ANALYZE_*.zip to ChatGPT.
echo ============================================================
pause
exit /b 0

:cancelled
echo.
echo Test cancelled.
exit /b 0

:failed
echo.
echo ============================================================
echo  VR TEST FAILED
echo  Keep the newest diagnostic ZIP/logs for analysis.
echo ============================================================
pause
exit /b %RC%
