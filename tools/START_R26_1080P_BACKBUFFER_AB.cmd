@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem A/B diagnostic ONLY: retain original 1920x1080 game backbuffer.
rem The OpenXR compositor stays at its recommended eye extent but scales
rem game pixels. This trades sharpness for controlled 2D/FPS regression test.
set "OUTRUN_VR_1080P_BACKBUFFER_AB=1"
echo [A/B] Test original 1080p game backbuffer; XR transport is upscaled.
call "%~dp0START_HERE.cmd"
exit /b %errorlevel%
