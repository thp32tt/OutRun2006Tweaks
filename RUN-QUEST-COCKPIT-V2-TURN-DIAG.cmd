@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 TURN DIAG - BOUNDED CAMERA PHASE TRACE.
echo Normal interpolation and verified F0 render scope stay ON.
echo Logs at most 24 positive + 24 negative steering samples.
set "RUNNER=%~dp0Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" set "RUNNER=%~dp0tools\Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" (
    echo [FAILED] Run-OutRunVRTest.ps1 was not found.
    pause
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON -QuestCockpitV2SkyProbe ON -QuestCockpitV2Interpolation ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Exit %ERRORCODE%. Collect-OutRunVRLogs.cmd archives the bounded turn trace.
pause
exit /b %ERRORCODE%
