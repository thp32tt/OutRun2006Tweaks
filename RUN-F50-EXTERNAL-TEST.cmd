@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo [F50 TEST] Usage: Drag a folder containing F50_External_Test.ovc onto this .cmd
  echo This MUST be extracted into a COPY of your game, with .F50_TEST_COPY marker.
  pause
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode F50 -F50ModelDir "%~1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo [FAILED] F50 external test failed. Use RESTORE-QUEST-APK-COCKPIT.cmd in copied game.
pause
exit /b %RESULT%
