@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRestore.ps1"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%
pause
exit /b %EC%
