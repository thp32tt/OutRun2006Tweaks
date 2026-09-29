@echo off
setlocal
cd /d "%~dp0"
title OutRun 2006 VR - R69 One Click Test

cls
echo ============================================================
echo  OUTRUN 2006 VR R69 TEST
echo  THIS IS THE ONLY FILE YOU NEED TO RUN.
echo ============================================================
echo.
echo  Mode: DX9Ex + D3D11 OpenXR host
echo  Profile: CORRECTNESS
echo  Fix focus: world rank, menu/finish text, selector/start shadow, stage sky transition
echo.
echo  The game will start automatically.
echo  After you exit the game, logs will be collected automatically.
echo  Upload only the newest OutRun2_VR_ANALYZE_*.zip to ChatGPT.
echo.

rem Remove obsolete user-facing launchers left by older test packages.
for %%F in (
  "OutRunVR-Backend-Selector.cmd"
  "OutRunVR-Slot-Selector.cmd"
  "OutRunVR-Visual-Isolation-Selector.cmd"
  "OutRunVR-EXE-Semantic-Selector.cmd"
  "START_HERE_SCREEN_DIAG.cmd"
  "START_HERE_EXE_SEMANTIC.cmd"
  "START_HERE_VR_FIX1.cmd"
  "START_HERE_VR_TEST_SELECTOR.cmd"
  "Collect-OutRunVRLogs.cmd"
) do (
  if exist "%%~F" del /q "%%~F" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Select-OutRunVRBackend.ps1" -Backend d3d9 -TestProfile CORRECTNESS -VariantId R69_FIXPACK
if errorlevel 1 goto :failed

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS
if errorlevel 1 goto :failed

echo.
echo ============================================================
echo  TEST COMPLETE
echo  Upload the newest OutRun2_VR_ANALYZE_*.zip only.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo TEST FAILED. Do not run another batch file.
echo Upload any newly-created OutRun2_VR_ANALYZE_*.zip, or a screenshot of this window.
pause
exit /b 1