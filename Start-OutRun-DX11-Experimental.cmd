@echo off
setlocal
cd /d "%~dp0"
tasklist /FI "IMAGENAME eq OR2006C2C.exe" 2>nul | find /I "OR2006C2C.exe" >nul
if not errorlevel 1 (
 echo [ERROR] Close the game before changing backend.
 exit /b 3
)
if not exist "%~dp0DX11_Experimental\dinput8.dll" exit /b 2
if not exist "%~dp0DX11_Experimental\outrun-vr-host.exe" exit /b 2
copy /Y "%~dp0DX11_Experimental\dinput8.dll" "%~dp0dinput8.dll" >nul || exit /b 4
copy /Y "%~dp0DX11_Experimental\outrun-vr-host.exe" "%~dp0outrun-vr-host.exe" >nul || exit /b 4
set "OUTRUN_DX11_FIRST_GAME_FRAME=1"
set "OUTRUN_DX11_FULL_GAME_FRAME="
echo [WARNING] Experimental DX11 selected, HMD runtime UNTESTED.
call "%~dp0Start-OutRun.cmd" vr
exit /b %errorlevel%
