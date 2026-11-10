@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto :bad_root

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" goto :no_powershell
if not exist "%~dp0QuestCockpit-CopyRun.ps1" goto :missing_launcher
if not exist "%~dp0QUEST_APK_COPYRUN_PAYLOAD\IDENTITY.json" goto :missing_payload
if not exist "%~dp0QuestCockpit-CopyRestore.ps1" goto :missing_restore

if /I "%~1"=="VERIFY" goto :verify
if not exist "%~dp0OR2006C2C.EXE" goto :missing_game

echo QUEST APK TURN: bounded camera phase diagnostic
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode TURN
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%. To revert, run RESTORE-QUEST-APK-COCKPIT.cmd
pause
exit /b %EC%

:verify
echo [VERIFY] QUEST APK TURN: bounded camera phase diagnostic
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRun.ps1" -Mode TURN -VerifyOnly
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Static package verification exit %EC%.
exit /b %EC%

:bad_root
echo [FAILED] Cannot enter the extracted game folder: %~dp0
if /I not "%~1"=="VERIFY" pause
exit /b 90
:no_powershell
echo [FAILED] Windows PowerShell not found: %PS%
if /I not "%~1"=="VERIFY" pause
exit /b 91
:missing_launcher
echo [FAILED] QuestCockpit-CopyRun.ps1 is missing.
echo Re-extract the ENTIRE QuestCockpitV2 COPY-RUN ZIP next to OR2006C2C.EXE.
if /I not "%~1"=="VERIFY" pause
exit /b 92
:missing_payload
echo [FAILED] QUEST_APK_COPYRUN_PAYLOAD\IDENTITY.json is missing.
echo Re-extract the ENTIRE COPY-RUN ZIP. Do not copy only the CMD files.
if /I not "%~1"=="VERIFY" pause
exit /b 93
:missing_restore
echo [FAILED] QuestCockpit-CopyRestore.ps1 is missing.
echo Re-extract the ENTIRE QuestCockpitV2 COPY-RUN ZIP before running the test.
if /I not "%~1"=="VERIFY" pause
exit /b 96
:missing_game
echo [FAILED] OR2006C2C.EXE is not in this folder.
echo Extract the ENTIRE COPY-RUN ZIP directly into the original OutRun 2006 game folder.
if /I not "%~1"=="VERIFY" pause
exit /b 95
