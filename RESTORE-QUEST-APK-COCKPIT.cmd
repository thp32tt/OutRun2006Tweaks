@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto :bad_root

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" goto :no_powershell
if not exist "%~dp0QuestCockpit-CopyRestore.ps1" goto :missing_restore

if /I "%~1"=="VERIFY" goto :verify
if not exist "%~dp0QUEST_APK_COPYRUN_ORIGINAL_BACKUP\original_files.json" goto :missing_backup

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRestore.ps1"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Exit %EC%
pause
exit /b %EC%

:verify
echo [VERIFY] QUEST APK COCKPIT restore launcher
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0QuestCockpit-CopyRestore.ps1" -VerifyOnly
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" echo [FAILED] Restore launcher verification exit %EC%.
exit /b %EC%

:bad_root
echo [FAILED] Cannot enter the extracted game folder: %~dp0
if /I not "%~1"=="VERIFY" pause
exit /b 90
:no_powershell
echo [FAILED] Windows PowerShell not found: %PS%
if /I not "%~1"=="VERIFY" pause
exit /b 91
:missing_restore
echo [FAILED] QuestCockpit-CopyRestore.ps1 is missing.
echo Re-extract the ENTIRE QuestCockpitV2 COPY-RUN ZIP.
if /I not "%~1"=="VERIFY" pause
exit /b 92
:missing_backup
echo [FAILED] No original backup manifest exists.
echo Run RUN-QUEST-APK-COCKPIT.cmd once before using restore.
if /I not "%~1"=="VERIFY" pause
exit /b 94
