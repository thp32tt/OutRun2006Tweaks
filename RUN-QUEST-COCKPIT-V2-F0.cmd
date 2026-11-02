@echo off
setlocal
cd /d "%~dp0"
echo QuestCockpitV2 experimental car F0 identity and occupant W-times-C.
echo This version additionally stages/restores original car F0 only within
echo original 0x49F3E0 player-car draw, NOT yet full APK render-frame parity.
echo If shaking or unstable, use RUN-QUEST-COCKPIT-V2.cmd for no F0.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 ON -QuestCockpitV2F0 ON
set "ERR=%ERRORLEVEL%"
echo.
echo Test finished: %ERR%. Send session logs.
pause
exit /b %ERR%
