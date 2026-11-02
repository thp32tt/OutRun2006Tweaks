@echo off
setlocal
cd /d "%~dp0"
echo QUEST COCKPIT V2 - STARTUP CRASH ISOLATION
echo 1 = Stable VR baseline (no cockpit hooks)
echo 2 = Native frame/callback hooks ONLY (no cockpit camera/model changes)
echo 3 = V2 cockpit, safe default (no F0, no LOD0)
echo 4 = F0 experiment (only after option 3 succeeds)
echo 5 = LOD0 experiment (only after option 3 succeeds)
echo.
choice /c 12345 /n /m "Select test [1-5]: "
set "OPTION=%ERRORLEVEL%"
if "%OPTION%"=="1" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 OFF
if "%OPTION%"=="2" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 OFF -QuestCockpitV2FrameOnly ON
if "%OPTION%"=="3" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 ON
if "%OPTION%"=="4" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 ON -QuestCockpitV2F0 ON
if "%OPTION%"=="5" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS -QuestCockpitV2 ON -QuestCockpitV2Lod0 ON
set "ERR=%ERRORLEVEL%"
echo.
echo Result exit code: %ERR%
echo If failed send the newest analysis ZIP under the game directory.
pause
exit /b %ERR%
