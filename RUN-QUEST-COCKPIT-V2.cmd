@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 - EXPERIMENTAL. Only native camera mode 1.
echo This test does not modify your original EXE or stable release.
set "RUNNER=%~dp0Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" set "RUNNER=%~dp0tools\Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" (
    echo [FAILED] Run-OutRunVRTest.ps1 was not found.
    echo Run QuestCockpit-CopyRun.ps1 first, or keep this CMD beside the repository tools folder.
    pause
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Test finished with code %ERRORCODE%.
echo For detailed logs, use RUN-QUEST-COCKPIT-V2-DIAG.cmd; normal play disables multi-GB tracing.
pause
exit /b %ERRORCODE%
