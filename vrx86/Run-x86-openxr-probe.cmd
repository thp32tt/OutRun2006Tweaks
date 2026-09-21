@echo off
setlocal
cd /d "%~dp0"
echo [OutRun x86 OpenXR Direct POC]
echo Virtual Desktop / VDXR should be running and Quest should be connected.
echo.
outrun-vr-x86-openxr-probe.exe
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo RESULT: PASS - 32-bit OpenXR D3D11 session creation succeeded.
) else (
  echo RESULT: FAIL - see the message above.
)
echo.
pause
exit /b %RC%
