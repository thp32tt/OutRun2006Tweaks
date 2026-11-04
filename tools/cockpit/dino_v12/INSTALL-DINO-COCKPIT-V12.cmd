@echo off
setlocal
cd /d "%~dp0"
echo OutRun 2006 - Dino 246 cockpit V12 experimental model
echo The original car model is backed up BEFORE any write.
echo Stop the game before applying.
set "GAME_ROOT=%~dp0"
if not "%~1"=="" set "GAME_ROOT=%~1"
if not exist "%GAME_ROOT%Cars\obj_plcar_dino_pmt.sz" (
  echo ERROR: Cars\obj_plcar_dino_pmt.sz not found under "%GAME_ROOT%".
  echo Extract the entire test ZIP into your existing OutRun 2006 game folder.
  pause
  exit /b 2
)
if exist "%~dp0DinoCockpitV12.exe" (
  "%~dp0DinoCockpitV12.exe" install --game "%GAME_ROOT%" --payload "%~dp0Dino246_CabinOnly_v12.dcm"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 "%~dp0dino_cockpit_pmt_patch_v12.py" install --game "%GAME_ROOT%" --payload "%~dp0Dino246_CabinOnly_v12.dcm"
  ) else (
    python "%~dp0dino_cockpit_pmt_patch_v12.py" install --game "%GAME_ROOT%" --payload "%~dp0Dino246_CabinOnly_v12.dcm"
  )
)
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" (
 echo Patch refused or failed. Your original file is preserved if verification failed.
) else (
 echo Model installed. Select Dino 246 GTS and switch to the cockpit (mode 1) in VR.
 echo Start with RUN-QUEST-COCKPIT-V2.cmd in the same folder.
)
pause
exit /b %CODE%