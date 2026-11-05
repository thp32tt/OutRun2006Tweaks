@echo off
setlocal EnableExtensions DisableDelayedExpansion
title OutRun2006 - DX11_RAW_VISUAL
if not exist "%~dp0OR2006C2C.EXE" (
  echo [ERROR] Missing original game EXE.
  pause
  exit /b 2
)
if not exist "%~dp0dinput8.dll" (
  echo [ERROR] Missing game hook.
  pause
  exit /b 3
)
if not exist "%~dp0Run-DX9ExFocusTest.ps1" (
  echo [ERROR] Missing test runner.
  pause
  exit /b 3
)
echo [MODE] DX11_RAW_VISUAL: original D3D9Ex fallback/input/FFB protected.
echo [LIMIT] GPU diagnostic only, full native game/HMD stereo NOT verified.
set "OUTRUN_DX11_TEST_MODE=RAW_VISUAL"
set "OUTRUN_DX11_FIRST_GAME_FRAME=1"
set "OUTRUN_DX11_FULL_GAME_FRAME=1"
set "OUTRUN_DX11_RAW_VISUAL_DIAGNOSTIC=1"
set "OUTRUN_DX11_GPU_SHARED_DESKTOP=0"
set "OUTRUN_VR_DX11_CENSUS=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-DX9ExFocusTest.ps1"
set "status=%errorlevel%"
echo [RESULT] %status%; see DX9EX_LOGS session ZIP with mode label.
pause
exit /b %status%
