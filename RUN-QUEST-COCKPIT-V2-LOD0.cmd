@echo off
setlocal
cd /d "%~dp0"
echo QuestCockpitV2 original APK occupant LOD0 A/B (EXPERIMENTAL).
echo Only exact original ROB01/ROB02 player model; world culling unchanged.
echo Verified F0 render scope stays ON so only occupant LOD changes.
set "RUNNER=%~dp0Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" set "RUNNER=%~dp0tools\Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" (
    echo [FAILED] Run-OutRunVRTest.ps1 was not found.
    pause
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON -QuestCockpitV2Lod0 ON
set "ERR=%ERRORLEVEL%"
echo.
echo Test finished: %ERR%. Send session logs.
pause
exit /b %ERR%
