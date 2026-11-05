@echo off
setlocal
cd /d "%~dp0"
echo QUEST APK SKY / CAR: bounded diagnostic
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode SKY
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%. To revert, run RESTORE-QUEST-APK-COCKPIT.cmd
pause
exit /b %EC%
