@echo off
setlocal
cd /d "%~dp0"
echo OUTRUN VR QUEST COCKPIT V2 - INTERPOLATION OFF A/B
echo This is a 60Hz simulation comparison for driving-only body shake.
echo Original game/car assets, stable focus branch and release are untouched.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2SkyProbe ON -QuestCockpitV2Interpolation OFF
set "ERR=%ERRORLEVEL%"
echo.
echo Exit code %ERR% - collect logs via existing script.
pause
exit /b %ERR%
