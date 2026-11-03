@echo off
setlocal
cd /d "%~dp0"
set "OUTRUN_DX11_FIRST_GAME_FRAME=1"
set "OUTRUN_DX11_FULL_GAME_FRAME="
set "OUTRUN_DX11_GPU_SHARED_DESKTOP="
echo Experimental DX11 first-game-frame capture; real HMD status UNTESTED.
call "%~dp0Start-OutRun.cmd" vr
