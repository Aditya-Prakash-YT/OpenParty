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
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Checking dependencies...
echo Checking dependencies... >> %LOGFILE%

:: Create portable tools directory
set TOOLS_DIR=%~dp0tools
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

:: ============================================================
:: 1. PYTHON
:: ============================================================
echo.
echo [1/5] Checking Python...
echo [1/5] Checking Python... >> %LOGFILE%
python --version >nul 2>&1
if %errorLevel% equ 0 goto :PythonOK
py --version >nul 2>&1
if %errorLevel% equ 0 goto :PythonOK

echo Python not found. Downloading Python 3.12.4 installer...
echo Python not found. Downloading installer... >> %LOGFILE%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python-installer.exe'" >> %LOGFILE% 2>&1

if not exist "%TEMP%\python-installer.exe" goto :PythonDownloadFailed

echo --------------------------------------------------
echo  Please follow the Python installation wizard.
echo  IMPORTANT: Check the box "Add Python.exe to PATH"!
echo --------------------------------------------------
"%TEMP%\python-installer.exe"
echo After Python is installed, press any key to continue...
pause
goto :PythonOK

:PythonDownloadFailed
echo [ERROR] Failed to download Python. Check install.log.
echo [ERROR] Failed to download Python. >> %LOGFILE%
goto :PythonDone

:PythonOK
echo Python is installed.
echo Python is installed. >> %LOGFILE%

:: Install pip requirements
echo Installing Python packages from requirements.txt...
echo Installing Python packages... >> %LOGFILE%
if exist "%~dp0..\app\requirements.txt" (
    python -m pip install -r "%~dp0..\app\requirements.txt" >> %LOGFILE% 2>&1
    if !errorLevel! neq 0 (
        py -m pip install -r "%~dp0..\app\requirements.txt" >> %LOGFILE% 2>&1
        if !errorLevel! neq 0 (
            echo [WARNING] Failed to install Python packages. Re-run setup after Python is installed.
            echo [WARNING] Failed to install Python packages. >> %LOGFILE%
        ) else (
            echo Python packages installed successfully.
            echo Python packages installed successfully. >> %LOGFILE%
        )
    ) else (
        echo Python packages installed successfully.
        echo Python packages installed successfully. >> %LOGFILE%
    )
) else (
    echo [WARNING] requirements.txt not found at ..\app\requirements.txt
    echo [WARNING] requirements.txt not found. >> %LOGFILE%
)

:PythonDone


:: ============================================================
:: 2. VLC
:: ============================================================
echo.
echo [2/5] Checking VLC...
echo [2/5] Checking VLC... >> %LOGFILE%
if exist "C:\Program Files\VideoLAN\VLC\vlc.exe" goto :VlcOK
if exist "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" goto :VlcOK
where vlc >nul 2>&1
if %errorLevel% equ 0 goto :VlcOK

echo VLC not found. Downloading VLC 3.0.23...
echo Downloading VLC... >> %LOGFILE%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     Invoke-WebRequest -Uri 'https://download.videolan.org/pub/videolan/vlc/3.0.23/win64/vlc-3.0.23-win64.exe' -OutFile '%TEMP%\vlc-installer.exe'" >> %LOGFILE% 2>&1

if not exist "%TEMP%\vlc-installer.exe" goto :VlcDownloadFailed

echo Running VLC installer silently...
echo Running VLC installer silently... >> %LOGFILE%
"%TEMP%\vlc-installer.exe" /S >> %LOGFILE% 2>&1

if exist "C:\Program Files\VideoLAN\VLC\vlc.exe" goto :VlcOK
if exist "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" goto :VlcOK
echo [WARNING] VLC may not have installed to the default location.
echo [WARNING] VLC install location unclear. >> %LOGFILE%
goto :VlcDone

:VlcDownloadFailed
echo [ERROR] Failed to download VLC. Check install.log.
echo [ERROR] Failed to download VLC. >> %LOGFILE%
goto :VlcDone

:VlcOK
echo VLC is installed.
echo VLC found. >> %LOGFILE%

:VlcDone


:: ============================================================
:: 3. ARIA2C (portable, no system changes)
:: ============================================================
echo.
echo [3/5] Checking aria2c...
echo [3/5] Checking aria2c... >> %LOGFILE%

where aria2c >nul 2>&1
if %errorLevel% equ 0 goto :AriaOK
if exist "%TOOLS_DIR%\aria2\aria2c.exe" goto :AriaOK
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\aria2c.exe" goto :AriaOK

echo aria2c not found. Downloading portable aria2c 1.37.0...
echo Downloading portable aria2c... >> %LOGFILE%
if not exist "%TOOLS_DIR%\aria2" mkdir "%TOOLS_DIR%\aria2"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     Invoke-WebRequest -Uri 'https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip' -OutFile '%TEMP%\aria2.zip'" >> %LOGFILE% 2>&1

if not exist "%TEMP%\aria2.zip" goto :AriaDownloadFailed

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%TEMP%\aria2.zip' -DestinationPath '%TEMP%\aria2_extract' -Force" >> %LOGFILE% 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Copy-Item (Get-ChildItem '%TEMP%\aria2_extract' -Filter 'aria2c.exe' -Recurse | Select-Object -First 1 -ExpandProperty FullName) '%TOOLS_DIR%\aria2\aria2c.exe' -Force" >> %LOGFILE% 2>&1

if exist "%TOOLS_DIR%\aria2\aria2c.exe" (
    echo aria2c portable installed to setup\tools\aria2\
    echo aria2c portable installed successfully. >> %LOGFILE%
    goto :AriaDone
)

:AriaDownloadFailed
echo [ERROR] Failed to install aria2c. Check install.log.
echo [ERROR] Failed to install aria2c. >> %LOGFILE%
goto :AriaDone

:AriaOK
echo aria2c is installed.
echo aria2c found. >> %LOGFILE%

:AriaDone


:: ============================================================
:: 4. SYNCPLAY
:: ============================================================
echo.
echo [4/5] Checking Syncplay...
echo [4/5] Checking Syncplay... >> %LOGFILE%
if exist "C:\Program Files\Syncplay\Syncplay.exe" goto :SyncplayOK
if exist "C:\Program Files (x86)\Syncplay\Syncplay.exe" goto :SyncplayOK
if exist "%TOOLS_DIR%\syncplay\Syncplay.exe" goto :SyncplayOK
where Syncplay >nul 2>&1
if %errorLevel% equ 0 goto :SyncplayOK

echo Syncplay not found. Downloading Syncplay 1.7.5 installer...
echo Downloading Syncplay installer... >> %LOGFILE%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     Invoke-WebRequest -Uri 'https://github.com/Syncplay/syncplay/releases/download/v1.7.5/Syncplay-1.7.5-Setup.exe' -OutFile '%TEMP%\Syncplay-Setup.exe'" >> %LOGFILE% 2>&1

if not exist "%TEMP%\Syncplay-Setup.exe" goto :SyncplayDownloadFailed

echo --------------------------------------------------
echo  Please follow the Syncplay installation wizard.
echo --------------------------------------------------
"%TEMP%\Syncplay-Setup.exe"
echo After Syncplay is installed, press any key to continue...
pause

if exist "C:\Program Files\Syncplay\Syncplay.exe" goto :SyncplayOK
if exist "C:\Program Files (x86)\Syncplay\Syncplay.exe" goto :SyncplayOK
echo [WARNING] Syncplay may not be in default directory.
echo [WARNING] Syncplay install location unclear. >> %LOGFILE%
goto :SyncplayDone

:SyncplayDownloadFailed
echo [ERROR] Failed to download Syncplay. Check install.log.
echo [ERROR] Failed to download Syncplay. >> %LOGFILE%
goto :SyncplayDone

:SyncplayOK
echo Syncplay is installed.
echo Syncplay found. >> %LOGFILE%

:SyncplayDone


:: ============================================================
:: 5. QBITTORRENT
:: ============================================================
echo.
echo [5/5] Checking qBittorrent...
echo [5/5] Checking qBittorrent... >> %LOGFILE%
if exist "C:\Program Files\qBittorrent\qbittorrent.exe" goto :QbitOK
if exist "C:\Program Files (x86)\qBittorrent\qbittorrent.exe" goto :QbitOK
where qbittorrent >nul 2>&1
if %errorLevel% equ 0 goto :QbitOK

echo qBittorrent not found. Downloading qBittorrent 4.6.5 installer...
echo Downloading qBittorrent installer... >> %LOGFILE%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     Invoke-WebRequest -Uri 'https://downloads.sourceforge.net/project/qbittorrent/qbittorrent-win32/qbittorrent-4.6.5/qbittorrent_4.6.5_x64_setup.exe' -OutFile '%TEMP%\qbittorrent-setup.exe'" >> %LOGFILE% 2>&1

if not exist "%TEMP%\qbittorrent-setup.exe" goto :QbitDownloadFailed

echo Running qBittorrent installer silently...
echo Running qBittorrent installer silently... >> %LOGFILE%
"%TEMP%\qbittorrent-setup.exe" /S >> %LOGFILE% 2>&1

if exist "C:\Program Files\qBittorrent\qbittorrent.exe" goto :QbitOK
if exist "C:\Program Files (x86)\qBittorrent\qbittorrent.exe" goto :QbitOK
echo [WARNING] qBittorrent installer completed, but may not be in default location.
echo [WARNING] qBittorrent install location unclear. >> %LOGFILE%
goto :QbitDone

:QbitDownloadFailed
echo [ERROR] Failed to download qBittorrent. Check install.log.
echo [ERROR] Failed to download qBittorrent. >> %LOGFILE%
goto :QbitDone

:QbitOK
echo qBittorrent is installed.
echo qBittorrent found. >> %LOGFILE%

:QbitDone


:: ============================================================
:: REGISTER .oparty FILE ASSOCIATION
:: ============================================================
echo.
echo Registering .oparty file association...
echo Registering .oparty file association... >> %LOGFILE%
assoc .oparty=OpenParty.File >> %LOGFILE% 2>&1
ftype OpenParty.File="%~dp0..\dist\OpenParty.exe" "%%1" >> %LOGFILE% 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Failed to register .oparty file association.
    echo [WARNING] Failed to register .oparty file association. >> %LOGFILE%
) else (
    echo .oparty files will now open with OpenParty.exe.
    echo .oparty file association registered. >> %LOGFILE%
)

echo.
echo ==================================================
echo  Setup complete!
echo  You can now launch: dist\OpenParty.exe
echo ==================================================
echo Setup complete. >> %LOGFILE%
pause
