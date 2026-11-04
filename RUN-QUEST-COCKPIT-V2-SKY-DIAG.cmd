@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 SKY DIAG - 90-PRESENT AGGREGATE ONLY.
echo Full draw telemetry OFF. Do not use this for normal play.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2SkyProbe ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Exit %ERRORCODE%. Collect-OutRunVRLogs.cmd archives limited sky diagnostics.
pause
exit /b %ERRORCODE%
