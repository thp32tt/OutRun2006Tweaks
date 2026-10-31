@echo off
setlocal
title OutRun 2006 R26 SAFE VR - Install And Run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL_AND_RUN.ps1" %*
if errorlevel 1 echo ERROR: Installation or launch failed - review the message above.
echo.
pause
