@echo off
setlocal
cd /d "%~dp0"
echo QUEST APK COCKPIT: copy and run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode NORMAL
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%. To revert, run RESTORE-QUEST-APK-COCKPIT.cmd
pause
exit /b %EC%
