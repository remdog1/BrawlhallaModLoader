@echo off
echo 🚀 Setting up Brawlhalla Mod Loader...
echo.

REM Check if git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Git is not installed or not in PATH
    echo Please install Git from https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Check if .gitmodules exists
if not exist ".gitmodules" (
    echo ❌ Error: .gitmodules not found
    echo Please run this script from the root of the repository
    pause
    exit /b 1
)

echo 🔄 Initializing core submodule...
git submodule update --init --recursive
if errorlevel 1 (
    echo ❌ Failed to initialize submodule
    pause
    exit /b 1
)

echo ✅ Core submodule initialized successfully

REM Install Python dependencies
if exist "requirements.txt" (
    echo 🔄 Installing main dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ⚠️  Warning: Failed to install main dependencies
    )
)

if exist "core\requirements.txt" (
    echo 🔄 Installing core dependencies...
    python -m pip install -r core\requirements.txt
    if errorlevel 1 (
        echo ⚠️  Warning: Failed to install core dependencies
    )
)

echo.
echo 🎉 Setup completed! You can now run the mod loader.
echo 📝 Note: If you encounter any issues, make sure you have:
echo    - Git installed
echo    - Python 3.7+ installed
echo    - Internet connection for downloading dependencies
echo.
pause
