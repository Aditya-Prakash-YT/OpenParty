@echo off
setlocal enabledelayedexpansion
title OpenParty Setup

:: Log setup
set LOGFILE="%~dp0install.log"
echo OpenParty Setup Log - %DATE% %TIME% > %LOGFILE%

:: Self-elevate check
net session >nul 2>&1
if %errorLevel% equ 0 (
    echo Administrator privileges confirmed.
    echo Administrator privileges confirmed. >> %LOGFILE%
) else (
    echo Requesting Administrator privileges...
    echo Requesting Administrator privileges... >> %LOGFILE%
    powershell -Command "Start-Process -FilePath '%0' -Verb RunAs"
    exit /b
)

echo Checking for winget...
echo Checking for winget... >> %LOGFILE%
winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] winget is not installed.
    echo [ERROR] winget is not installed. >> %LOGFILE%
    echo Please install 'App Installer' from the Microsoft Store, or download it from Microsoft's winget-cli GitHub releases.
    echo Press any key to exit...
    pause
    exit /b
)

echo Winget found. Checking dependencies...
echo Winget found. Checking dependencies... >> %LOGFILE%

:: Check and Install VLC
echo Checking VLC media player...
winget list --id VideoLAN.VLC >nul 2>&1
if %errorLevel% equ 0 (
    echo VLC is already installed.
    echo VLC is already installed. >> %LOGFILE%
) else (
    echo Installing VLC...
    echo Installing VLC... >> %LOGFILE%
    winget install --id VideoLAN.VLC --version 3.0.23 -e --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if !errorLevel! neq 0 (
        echo [ERROR] Failed to install VLC. See install.log for details.
    ) else (
        echo VLC installed successfully.
    )
)

:: Check and Install aria2
echo Checking aria2...
winget list --id aria2.aria2 >nul 2>&1
if %errorLevel% equ 0 (
    echo aria2 is already installed.
    echo aria2 is already installed. >> %LOGFILE%
) else (
    echo Installing aria2...
    echo Installing aria2... >> %LOGFILE%
    winget install --id aria2.aria2 --version 1.37.0 -e --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if !errorLevel! neq 0 (
        echo [ERROR] Failed to install aria2. See install.log for details.
    ) else (
        echo aria2 installed successfully.
    )
)

:: Check and Install Syncplay
echo Checking Syncplay...
winget list --id Syncplay.Syncplay >nul 2>&1
if %errorLevel% equ 0 (
    echo Syncplay is already installed.
    echo Syncplay is already installed. >> %LOGFILE%
) else (
    echo Installing Syncplay (via winget fallback to direct installer)...
    echo Installing Syncplay... >> %LOGFILE%
    winget install --id Syncplay.Syncplay --version 1.7.5 -e --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    if !errorLevel! neq 0 (
        echo Winget failed. Trying direct installer fallback...
        echo Winget failed for Syncplay. Trying direct installer... >> %LOGFILE%
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/Syncplay/syncplay/releases/download/v1.7.5/Syncplay-1.7.5-Setup.exe' -OutFile '%TEMP%\SyncplaySetup.exe'" >> %LOGFILE% 2>&1
        "%TEMP%\SyncplaySetup.exe" /S >> %LOGFILE% 2>&1
        if !errorLevel! neq 0 (
            echo [ERROR] Failed to install Syncplay. See install.log for details.
        ) else (
            echo Syncplay installed successfully via direct installer.
            echo Syncplay installed successfully via direct installer. >> %LOGFILE%
        )
    ) else (
        echo Syncplay installed successfully.
    )
)

:: Register .oparty file association
echo Registering .oparty file association...
echo Registering .oparty file association... >> %LOGFILE%
assoc .oparty=OpenParty.File >> %LOGFILE% 2>&1
ftype OpenParty.File="python" "%~dp0..\app\main.py" "%%1" >> %LOGFILE% 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Failed to register .oparty file association.
    echo [WARNING] Failed to register .oparty file association. >> %LOGFILE%
) else (
    echo .oparty file association registered.
)

echo.
echo Setup complete. You can now open OpenParty.
echo Setup complete. You can now open OpenParty. >> %LOGFILE%
pause
