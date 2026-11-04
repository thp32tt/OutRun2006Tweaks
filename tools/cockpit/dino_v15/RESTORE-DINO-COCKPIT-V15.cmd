@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "GAME_ROOT=%~dp0."
if not "%~1"=="" set "GAME_ROOT=%~1\."
if not exist "%~dp0DinoCockpitV15.exe" (
 echo [ERROR] DinoCockpitV15.exe is missing.
 pause
 exit /b 2
)
echo [R1 PATH FIX] Corrected Windows quoted trailing-backslash arguments.
echo Restoring exact SHA-verified Dino original from .dino-v12-original.bak ...
"%~dp0DinoCockpitV15.exe" restore --game "%GAME_ROOT%"
set "RESULT=%ERRORLEVEL%"
if "%RESULT%"=="0" echo [RESTORED] Verified original Dino PMT restored.
pause
exit /b %RESULT%
