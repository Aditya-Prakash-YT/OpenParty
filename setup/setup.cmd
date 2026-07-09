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

:: Check for Python
echo Checking for Python...
echo Checking for Python... >> %LOGFILE%
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Python is not installed or not in PATH.
    echo [WARNING] Python is not installed. Downloading installer... >> %LOGFILE%
    echo Downloading Python installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python-installer.exe'" >> %LOGFILE% 2>&1
    echo --------------------------------------------------
    echo Please follow the Python installation prompt.
    echo IMPORTANT: Make sure to check the box "Add Python.exe to PATH" at the bottom of the installer!
    echo --------------------------------------------------
    "%TEMP%\python-installer.exe"
    echo After Python is installed, press any key to continue...
    pause
) else (
    echo Python is installed.
    echo Python is installed. >> %LOGFILE%
)

:: Install Python Requirements
echo Checking and installing Python dependencies...
echo Checking and installing Python dependencies... >> %LOGFILE%
if exist "%~dp0..\app\requirements.txt" (
    python -m pip install -r "%~dp0..\app\requirements.txt" >> %LOGFILE% 2>&1
    if !errorLevel! neq 0 (
        py -m pip install -r "%~dp0..\app\requirements.txt" >> %LOGFILE% 2>&1
        if !errorLevel! neq 0 (
            echo [WARNING] Failed to install Python packages. You may need to close and run setup.cmd again if you just installed Python.
        ) else (
            echo Python packages installed successfully.
        )
    ) else (
        echo Python packages installed successfully.
    )
) else (
    echo [WARNING] requirements.txt not found.
    echo [WARNING] requirements.txt not found. >> %LOGFILE%
)

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

:: Create portable tools directory
set TOOLS_DIR=%~dp0tools
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

:: Check and Install aria2
echo Checking aria2...
where aria2c >nul 2>&1
if %errorLevel% equ 0 (
    echo aria2c found on PATH.
    echo aria2c found on PATH. >> %LOGFILE%
) else if exist "%TOOLS_DIR%\aria2\aria2c.exe" (
    echo aria2c found in portable tools.
    echo aria2c found in portable tools. >> %LOGFILE%
) else (
    echo aria2c not found. Attempting winget install...
    echo Installing aria2 via winget... >> %LOGFILE%
    winget install --id aria2.aria2 --version 1.37.0 -e --accept-package-agreements --accept-source-agreements >> %LOGFILE% 2>&1
    where aria2c >nul 2>&1
    if !errorLevel! neq 0 (
        echo Winget failed or aria2c not on PATH. Downloading portable version...
        echo Downloading portable aria2c... >> %LOGFILE%
        if not exist "%TOOLS_DIR%\aria2" mkdir "%TOOLS_DIR%\aria2"
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip' -OutFile '%TEMP%\aria2.zip'" >> %LOGFILE% 2>&1
        powershell -Command "Expand-Archive -Path '%TEMP%\aria2.zip' -DestinationPath '%TEMP%\aria2_extract' -Force" >> %LOGFILE% 2>&1
        powershell -Command "Copy-Item '%TEMP%\aria2_extract\aria2-1.37.0-win-64bit-build1\aria2c.exe' '%TOOLS_DIR%\aria2\aria2c.exe' -Force" >> %LOGFILE% 2>&1
        if exist "%TOOLS_DIR%\aria2\aria2c.exe" (
            echo aria2c portable installed successfully.
            echo aria2c portable installed successfully. >> %LOGFILE%
        ) else (
            echo [ERROR] Failed to install aria2c. See install.log.
            echo [ERROR] Failed to install aria2c. >> %LOGFILE%
        )
    ) else (
        echo aria2c installed successfully via winget.
    )
)

:: Check and Install Syncplay
echo Checking Syncplay...
where Syncplay >nul 2>&1
if %errorLevel% equ 0 (
    echo Syncplay found on PATH.
    echo Syncplay found on PATH. >> %LOGFILE%
) else if exist "C:\Program Files\Syncplay\Syncplay.exe" (
    echo Syncplay found in Program Files.
    echo Syncplay found in Program Files. >> %LOGFILE%
) else if exist "C:\Program Files (x86)\Syncplay\Syncplay.exe" (
    echo Syncplay found in Program Files x86.
    echo Syncplay found in Program Files x86. >> %LOGFILE%
) else if exist "%TOOLS_DIR%\syncplay\Syncplay.exe" (
    echo Syncplay found in portable tools.
    echo Syncplay found in portable tools. >> %LOGFILE%
) else (
    echo Syncplay not found. Downloading installer...
    echo Downloading Syncplay installer... >> %LOGFILE%
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/Syncplay/syncplay/releases/download/v1.7.5/Syncplay-1.7.5-Setup.exe' -OutFile '%TEMP%\Syncplay-Setup.exe'" >> %LOGFILE% 2>&1
    echo --------------------------------------------------
    echo Please follow the Syncplay installation prompt.
    echo --------------------------------------------------
    "%TEMP%\Syncplay-Setup.exe"
    echo After Syncplay is installed, press any key to continue...
    pause
    :: Verify it actually installed
    if exist "C:\Program Files\Syncplay\Syncplay.exe" (
        echo Syncplay installed successfully.
        echo Syncplay installed successfully. >> %LOGFILE%
    ) else if exist "C:\Program Files (x86)\Syncplay\Syncplay.exe" (
        echo Syncplay installed successfully.
        echo Syncplay installed successfully. >> %LOGFILE%
    ) else (
        echo [WARNING] Syncplay does not appear to be installed in the default directory.
        echo [WARNING] Syncplay does not appear to be installed in the default directory. >> %LOGFILE%
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
echo Setup complete. You can now open %cd%/../dist/OpenParty.exe.
echo Setup complete. You can now open %cd%/../dist/OpenParty.exe. >> %LOGFILE%
pause

