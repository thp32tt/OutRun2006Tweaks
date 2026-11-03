@echo off
setlocal
cd /d "%~dp0"
echo Quest cockpit V2: experimental reversible PMT glass brightness control.
echo The game must be closed before enabling/disabling.
powershell.exe -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpitV2-GlassControl.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
