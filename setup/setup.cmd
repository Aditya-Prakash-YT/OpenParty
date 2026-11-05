@echo off
setlocal
title OpenParty Setup

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "SETUP_EXIT=%ERRORLEVEL%"

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -RepairCurrentUserSettings
if not "%ERRORLEVEL%"=="0" set "SETUP_EXIT=1"

if "%SETUP_EXIT%"=="0" (
    echo.
    echo OpenParty setup completed successfully.
) else (
    echo.
    echo OpenParty setup did not complete. See "%ProgramData%\OpenParty\install.log" for details.
)

pause
exit /b %SETUP_EXIT%
