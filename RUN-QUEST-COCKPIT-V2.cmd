@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 - EXPERIMENTAL. Only native camera mode 1.
echo This test does not modify your original EXE or stable release.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Test finished with code %ERRORCODE%.
echo Send logs from the logs folder and any OUTRUNVR_LAUNCH_ERROR.txt.
pause
exit /b %ERRORCODE%
