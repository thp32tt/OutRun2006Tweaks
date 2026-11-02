@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 - STARTUP FAILURE DIAGNOSTIC
echo 1 = Baseline VR, cockpit OFF and game logging ON
echo 2 = Native frame hooks only; no cockpit render change
echo 3 = Full V2 without F0 or LOD0
echo 4 = V2 + F0 (only after 3 works)
echo 5 = V2 + LOD0 (only after 3 works)
echo 6 = CLASSIC D3D9 no cockpit (try this first if option 1 crashed)
echo.
choice /c 123456 /n /m "Select [1-6]: "
set "MODE=%ERRORLEVEL%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-QuestCockpitV2-CrashDiag.ps1" -Test %MODE%
set "ERR=%ERRORLEVEL%"
echo.
echo Result code: %ERR%
echo If crashed, send newest analysis ZIP. WER mini-dumps are under VR_CRASH_DUMPS.
pause
exit /b %ERR%
