@echo off
REM Brawlhalla Mod Loader - Windows Setup Script
REM This script runs the universal Python setup script

echo ============================================================
echo Brawlhalla Mod Loader - Windows Setup
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    echo.
    pause
    exit /b 1
)

echo Running universal setup script...
echo.

REM Run the Python setup script
python setup_universal.py

REM Check if setup was successful
if errorlevel 1 (
    echo.
    echo Setup completed with errors. Please review the output above.
) else (
    echo.
    echo Setup completed successfully!
)

echo.
pause

