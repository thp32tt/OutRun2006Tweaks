@echo off
setlocal
cd /d "%~dp0"
echo Restoring byte-exact original Dino 246 PMT from verified backup...
set "GAME_ROOT=%~dp0"
if not "%~1"=="" set "GAME_ROOT=%~1"
if exist "%~dp0DinoCockpitV13.exe" (
  "%~dp0DinoCockpitV13.exe" restore --game "%GAME_ROOT%"
) else (
  py -3 "%~dp0dino_cockpit_pmt_patch_v13.py" restore --game "%GAME_ROOT%"
)
set "CODE=%ERRORLEVEL%"
pause
exit /b %CODE%