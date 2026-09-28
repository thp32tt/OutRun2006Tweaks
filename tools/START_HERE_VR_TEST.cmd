@echo off
setlocal
cd /d "%~dp0"
title OutRun 2006 VR One-Click

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Invoke-OutRunVROneClick.ps1" -Backend auto -TestProfile CORRECTNESS
if errorlevel 1 goto :failed

echo.
echo ============================================================
echo  VR TEST COMPLETE
echo  The newest OutRun2_VR_ANALYZE_*.zip contains this session.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo ============================================================
echo  VR TEST FAILED
echo  Keep the newest diagnostic ZIP/logs for analysis.
echo ============================================================
pause
exit /b 1
