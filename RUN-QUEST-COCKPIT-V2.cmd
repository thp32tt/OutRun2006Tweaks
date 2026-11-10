@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 - EXPERIMENTAL. Only native camera mode 1.
echo This test does not modify your original EXE or stable release.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Test finished with code %ERRORCODE%.
echo For detailed logs, use RUN-QUEST-COCKPIT-V2-DIAG.cmd; normal play disables multi-GB tracing.
pause
exit /b %ERRORCODE%
