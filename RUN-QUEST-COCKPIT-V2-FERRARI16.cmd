@echo off
setlocal
cd /d "%~dp0"
set "RUNNER=%~dp0Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" set "RUNNER=%~dp0tools\Run-OutRunVRTest.ps1"
if not exist "%RUNNER%" (
  echo [FAILED] Run-OutRunVRTest.ps1 was not found.
  pause
  exit /b 2
)
echo Ferrari external models on latest known-good Quest cockpit path.
powershell -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -TestProfile CORRECTNESS -QuestCockpitV2ReleaseParity ON -QuestCockpitV2 ON -QuestCockpitV2F0 ON -ExternalFerrariTest ON -F50ExternalModel ON
set "ERRORCODE=%ERRORLEVEL%"
echo.
echo Test finished with code %ERRORCODE%.
pause
exit /b %ERRORCODE%
