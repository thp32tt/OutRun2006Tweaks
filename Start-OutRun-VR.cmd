@echo off
setlocal
cd /d "%~dp0"

rem Release policy: direct OR2006C2C.exe is normal 2D.
rem This launcher is the only supported VR entrypoint for the beta package.
set "OUTRUN_VR_LAUNCH=1"
set "OUTRUN_VR_FILE_LOG=0"

start "" "%~dp0OR2006C2C.exe" -VR.Enabled=true -VR.AutoLaunchHost=true -VR.PreferD3D9Ex=true -VR.DirectGpuOnly=true -VR.Telemetry=false -VR.FileLogging=false
endlocal
