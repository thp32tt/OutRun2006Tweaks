@echo off
setlocal
cd /d "%~dp0"

rem Remove obsolete user-facing selectors from older test packages.
for %%F in (
  "OutRunVR-Backend-Selector.ps1"
  "OutRunVR-Backend-Selector.cmd"
  "OutRunVR-Slot-Selector.ps1"
  "OutRunVR-Slot-Selector.cmd"
  "OutRunVR-Visual-Isolation-Selector.ps1"
  "OutRunVR-Visual-Isolation-Selector.cmd"
  "OutRunVR-EXE-Semantic-Selector.ps1"
  "OutRunVR-EXE-Semantic-Selector.cmd"
  "START_HERE_SCREEN_DIAG.cmd"
  "START_HERE_EXE_SEMANTIC.cmd"
  "START_HERE_VR_FIX1.cmd"
  "START_HERE_VR_TEST_SELECTOR.cmd"
) do (
  if exist "%%~F" del /q "%%~F" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0OutRunVR-Test-Selector.ps1"
if errorlevel 1 pause
