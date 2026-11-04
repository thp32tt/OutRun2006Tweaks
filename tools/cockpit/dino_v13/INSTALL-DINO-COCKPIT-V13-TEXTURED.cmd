@echo off
setlocal
cd /d "%~dp0"
echo OutRun 2006 Dino 246 GTS V13 Textured Cockpit [Experimental]
echo Original PMT SHA verification, automatic backup, two added BC1 leather textures.
echo STOP THE GAME BEFORE INSTALLING!
set "GAME_ROOT=%~dp0"
if not "%~1"=="" set "GAME_ROOT=%~1"
if not exist "%GAME_ROOT%Cars\obj_plcar_dino_pmt.sz" (
 echo ERROR: Game model file Cars\obj_plcar_dino_pmt.sz not found.
 echo This tool does not copy APK assets into the game.
 pause
 exit /b 2
)
if exist "%~dp0DinoCockpitV13.exe" (
  "%~dp0DinoCockpitV13.exe" install --game "%GAME_ROOT%" --payload "%~dp0Dino246_CabinOnly_v12.dcm" --textures-dir "%~dp0"
) else (
  py -3 "%~dp0dino_cockpit_pmt_patch_v13.py" install --game "%GAME_ROOT%" --payload "%~dp0Dino246_CabinOnly_v12.dcm" --textures-dir "%~dp0"
)
set "CODE=%ERRORLEVEL%"
if "%CODE%"=="0" (
 echo Installed TEXTURED Dino 246 cockpit. Now run RUN-QUEST-COCKPIT-V2.cmd and select camera mode 1.
) else (
 echo Install refused or failed. The tool did not replace unknown original files.
)
pause
exit /b %CODE%