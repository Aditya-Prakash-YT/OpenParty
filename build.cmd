@echo off
setlocal enabledelayedexpansion
title OpenParty - Build Distributable

:: Change working directory to script's directory (repo root)
cd /d "%~dp0"

echo ============================================================
echo               OpenParty Distributable Builder
echo ============================================================
echo.

:: 1. Check Python
echo [1/4] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found on PATH. Please install Python 3.12+ and add it to PATH.
    pause
    exit /b 1
)

:: 2. Ensure PyInstaller is installed
echo [2/4] Verifying PyInstaller...
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] PyInstaller not detected. Installing PyInstaller...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install PyInstaller via pip.
        pause
        exit /b 1
    )
)

:: Ensure obsolete backport pathlib is removed if present (incompatible with PyInstaller)
python -c "import pathlib, sys; sys.exit(0 if 'site-packages' not in getattr(pathlib, '__file__', '') else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Removing obsolete backport pathlib package...
    python -m pip uninstall -y pathlib >nul 2>&1
)

:: 3. Run Test Suite
echo [3/4] Running automated test suite before building...
python run_tests.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Unit tests failed! Dist build aborted.
    pause
    exit /b 1
)
echo Tests passed successfully!

:: 4. Build with PyInstaller
echo.
echo [4/4] Building OpenParty.exe via PyInstaller (spec: OpenParty.spec)...
python -m PyInstaller --clean -y OpenParty.spec
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] PyInstaller build failed! Check output above.
    pause
    exit /b 1
)

echo.
if exist "dist\OpenParty.exe" (
    echo ============================================================
    echo  SUCCESS: Distributable build complete!
    echo  Output binary: dist\OpenParty.exe
    echo ============================================================
) else (
    echo [ERROR] Build completed without error code, but dist\OpenParty.exe not found.
    pause
    exit /b 1
)

echo.
pause
exit /b 0
