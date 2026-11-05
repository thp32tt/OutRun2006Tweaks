@echo off
setlocal
cd /d "%~dp0"
echo QUEST APK COCKPIT + DINO FITV6: copy and run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode DINO
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%. To revert, run RESTORE-QUEST-APK-COCKPIT.cmd
pause
exit /b %EC%
