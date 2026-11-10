@echo off
setlocal
cd /d "%~dp0"
echo QuestCockpitV2 verified player-car F0 render scope.
echo The main cockpit launcher now uses the same F0 scope by default.
echo This alias is kept for compatibility with older test instructions.
set "RUNNER=%~dp0Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" set "RUNNER=%~dp0tools\Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" (
    echo [FAILED] Run-OutRunVRTest.ps1 was not found.
    pause
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON
set "ERR=%ERRORLEVEL%"
echo.
echo Test finished: %ERR%. Send session logs.
pause
exit /b %ERR%
