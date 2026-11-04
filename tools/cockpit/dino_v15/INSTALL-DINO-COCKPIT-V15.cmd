@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "GAME_ROOT=%~dp0."
if not "%~1"=="" set "GAME_ROOT=%~1\."
echo ===================================================
echo OUTRUN 2006 Dino 246 GTS V15 LHD Full-Texture Test
echo ===================================================
echo Experimental / NOT HMD VALIDATED / 70 groups, 19 BC1 textures.
echo [R1 PATH FIX] Corrected Windows quoted trailing-backslash arguments.
echo.
if not exist "%GAME_ROOT%\Cars\obj_plcar_dino_pmt.sz" (
  echo [ERROR] Cars\obj_plcar_dino_pmt.sz is missing.
  echo Copy this ZIP beside OR2006C2C.exe in the real OutRun game folder.
  echo No original game assets are distributed by this test package.
  pause
  exit /b 2
)
if not exist "%~dp0DinoCockpitV15.exe" (
  echo [ERROR] DinoCockpitV15.exe missing from ZIP; re-extract all files.
  pause
  exit /b 2
)
"%~dp0DinoCockpitV15.exe" install --game "%GAME_ROOT%" --payload "%~dp0Dino246_Cockpit_LHD_v15.dcm" --textures-dir "%~dp0."
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo [FAILED] SHA256 mismatch, unknown mod version, missing texture, or invalid PMT.
  echo Previous game data is protected by the patcher. Do not delete any backup.
  pause
  exit /b %RESULT%
)
echo.
echo [SUCCESS] Dino v15 LHD PMT test content installed.
echo [NEXT] Run RUN-QUEST-COCKPIT-V2.cmd, select Dino 246 GTS and camera 1.
echo [RESTORE] RESTORE-DINO-COCKPIT-V15.cmd after testing.
pause
exit /b 0
