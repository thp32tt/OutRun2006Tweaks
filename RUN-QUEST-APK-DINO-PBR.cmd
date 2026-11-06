@echo off
setlocal
cd /d "%~dp0"
echo QUEST APK COCKPIT + DINO OVC3 PBR: verified copy and run
if not exist "%~dp0QuestCockpit-CopyRun.ps1" (
    echo [FAILED] QuestCockpit-CopyRun.ps1 not found next to this launcher.
    pause
    exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode PBR
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%. Restore with RESTORE-QUEST-APK-COCKPIT.cmd
pause
exit /b %EC%
