@echo off
setlocal EnableExtensions DisableDelayedExpansion
if /I "%~1"=="VERIFY" (
  call "%~dp0RUN-QUEST-APK-COCKPIT.cmd" VERIFY
) else (
  call "%~dp0RUN-QUEST-APK-COCKPIT.cmd" PASSENGER
)
exit /b %ERRORLEVEL%
