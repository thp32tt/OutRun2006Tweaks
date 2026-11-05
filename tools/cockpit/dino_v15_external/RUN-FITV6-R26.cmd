@echo off
setlocal
pushd "%~dp0"

if not exist "OR2006C2C.EXE" (
  echo.
  echo [FAILED] OR2006C2C.EXE is not in this folder.
  echo Copy ALL files from this ZIP directly into the OutRun 2006 game folder,
  echo so this CMD file is beside OR2006C2C.EXE, then run it again.
  echo.
  echo Current folder: %CD%
  echo No original game files were changed.
  popd
  pause
  exit /b 2
)

if not exist "RUN_DX9EX_TEST.cmd" (
  echo [FAILED] RUN_DX9EX_TEST.cmd is missing from this package.
  popd
  pause
  exit /b 3
)

call "%~dp0RUN_DX9EX_TEST.cmd"
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
