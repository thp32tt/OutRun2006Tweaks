@echo off
setlocal
cd /d "%~dp0"
set "OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=1"
echo Ferrari external fixed-function stereo A/B.
echo PBR normal/ORM maps are intentionally bypassed for this diagnostic run.
call "%~dp0RUN-QUEST-COCKPIT-V2-FERRARI16.cmd"
exit /b %ERRORLEVEL%
