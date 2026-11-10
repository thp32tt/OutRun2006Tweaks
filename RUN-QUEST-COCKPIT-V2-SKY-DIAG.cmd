@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 SKY DIAG - 90-PRESENT AGGREGATE ONLY.
echo Full draw telemetry OFF. Do not use this for normal play.
set "RUNNER=%~dp0Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" set "RUNNER=%~dp0tools\Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" (
    echo [FAILED] Run-OutRunVRTest.ps1 was not found.
    pause
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON -QuestCockpitV2SkyProbe ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Exit %ERRORCODE%. Collect-OutRunVRLogs.cmd archives limited sky diagnostics.
pause
exit /b %ERRORCODE%
