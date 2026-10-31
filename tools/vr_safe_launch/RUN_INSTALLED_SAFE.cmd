@echo off
setlocal
cd /d "%~dp0"
if not exist "OR2006C2C.EXE" (
 echo ERROR: This must be run in the real OutRun game folder.
 pause
 exit /b 2
)
if not exist "Run-DX9ExFocusTest.ps1" (
 echo ERROR: Official DX9Ex PowerShell launcher is missing.
 pause
 exit /b 3
)
call "%~dp0RUN_DX9EX_TEST.cmd"
