@echo off
setlocal
cd /d "%~dp0"
echo QuestCockpitV2 original APK occupant LOD0 A/B (EXPERIMENTAL).
echo Only exact original ROB01/ROB02 player model; world culling unchanged.
echo Normal and F0 scopes are OFF by default. Compare normal V2 result.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 ON -QuestCockpitV2Lod0 ON
set "ERR=%ERRORLEVEL%"
echo.
echo Test finished: %ERR%. Send session logs.
pause
exit /b %ERR%
