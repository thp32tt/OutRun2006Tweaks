@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo [FAILED] Drag a validated Dino OVC3 model onto this batch file.
  echo The original game folder and models will not be modified.
  pause
  exit /b 2
)
set "MODEL=%~f1"
if not exist "%MODEL%" (
  echo [FAILED] PBR OVC3 input does not exist: "%MODEL%"
  pause
  exit /b 2
)
set "OUTPUT=%~dp0Dino-OVC3-PBR-COPYRUN.zip"
if exist "%OUTPUT%" (
  echo [FAILED] The package already exists. Move or rename it to preserve the previous build.
  pause
  exit /b 3
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0CREATE-DINO-PBR-PACKAGE.py" --artifact-dir "%~dp0" --ovc3 "%MODEL%" --out-zip "%OUTPUT%"
) else (
  python "%~dp0CREATE-DINO-PBR-PACKAGE.py" --artifact-dir "%~dp0" --ovc3 "%MODEL%" --out-zip "%OUTPUT%"
)
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo [FAILED] PBR test ZIP was not created. Do not install mixed-source DLL/host.
) else (
  echo [PASS] PBR copy-run ZIP was created with an exact-SHA backend.
  echo Extract it only to a COPY of the original OutRun game folder.
)
pause
exit /b %EC%
