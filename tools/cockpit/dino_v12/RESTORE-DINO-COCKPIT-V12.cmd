@echo off
setlocal
cd /d "%~dp0"
echo Restoring original Dino PMT from the verified backup...
set "GAME_ROOT=%~dp0"
if not "%~1"=="" set "GAME_ROOT=%~1"
if exist "%~dp0DinoCockpitV12.exe" (
  "%~dp0DinoCockpitV12.exe" restore --game "%GAME_ROOT%"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 "%~dp0dino_cockpit_pmt_patch_v12.py" restore --game "%GAME_ROOT%"
  ) else (
    python "%~dp0dino_cockpit_pmt_patch_v12.py" restore --game "%GAME_ROOT%"
  )
)
set "CODE=%ERRORLEVEL%"
if "%CODE%"=="0" (echo Original Dino asset verified and restored.) else (echo Restore failed. Keep the .dino-v12-original.bak backup.)
pause
exit /b %CODE%