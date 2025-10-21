@echo off
:: Warp Account Manager Launcher - Enhanced Edition
:: Automatic installation and startup script with admin elevation

:: Check for admin rights and auto-elevate if needed
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Warp Account Manager - Installation and Startup
chcp 65001 >nul 2>&1

echo.
echo ====================================================
echo    Warp Account Manager - Automatic Installation
echo ====================================================
echo.

:: Administrator permission verified
echo [1/6] Administrator privileges verified
echo.

:: Check if Python is installed
echo [2/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Python 3.8 or higher is required.
    echo Please download and install Python from https://python.org
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

:: Check if pip is installed
echo [3/6] Checking pip installation...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found!
    echo.
    echo pip should come with Python.
    echo Try reinstalling Python.
    echo.
    pause
    exit /b 1
)
echo [OK] pip found
echo.

:: Database file check
echo [4/6] Checking database file...
if exist "accounts.db" (
    echo [OK] Database file exists
) else (
    echo [INFO] Database file will be created
)
echo.

:: Start Warp Account Manager
echo [5/5] Starting Warp Account Manager...
echo.
echo ====================================================
echo    Installation completed - Starting application
echo ====================================================
echo.

:: Navigate to script directory
cd /d "%~dp0"

if exist "warp_account_manager.py" (
    echo Opening Warp Account Manager...
    echo.
    echo NOTE: Do not close this window! This console window
    echo       must remain open while the application is running.
    echo.
    python warp_account_manager.py

    echo.
    echo Warp Account Manager closed.
) else (
    echo [ERROR] warp_account_manager.py file not found!
    echo.
    echo Current directory: %CD%
    echo Script directory: %~dp0
    echo.
    echo Please ensure all files are in the correct location.
)

echo.
echo Press any key to exit...
pause >nul
