@echo off
setlocal
cd /d "%~dp0"
if not exist "OR2006C2C.EXE" (
  echo ERROR: Original OR2006C2C.EXE is missing.
  echo Extract this ENTIRE package into the original OutRun 2006 game folder.
  pause
  exit /b 2
)
if not exist "backends\d3d9\dinput8.dll" (
  echo ERROR: DX9Ex compiled game DLL is missing.
  echo Use the complete PC FAST ZIP, not scripts alone.
  pause
  exit /b 3
)
if not exist "backends\d3d9\outrun-vr-host.exe" (
  echo ERROR: OpenXR host executable is missing.
  pause
  exit /b 4
)
rem The PS1 handles first-run safe backend selection and preserves existing
rem DXVK/2D selections. Never overwrite a selected backend here.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-OutRunVRTest.ps1" -TestProfile CORRECTNESS
set "code=%ERRORLEVEL%"
if not "%code%"=="0" (
  echo VR launch failed: exit code %code%.
  echo Inspect OUTRUNVR_LAUNCH_ERROR.txt and upload logs.
  pause
)
exit /b %code%
