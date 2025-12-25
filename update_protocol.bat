@echo off
echo ================================================
echo Brawlhalla Mod Loader Protocol Update
echo ================================================
echo.
echo This will update the bmod:// protocol registration
echo to point to the current mod loader executable.
echo.
echo You may be prompted for administrator privileges.
echo Please click "Yes" when asked.
echo.
pause

echo.
echo Registering protocol...
echo.

powershell -Command "Start-Process '%~dp0dist\Brawlhalla Mod Loader 2025 Beta.exe' -Verb RunAs"

echo.
echo Protocol registration triggered!
echo.
echo The mod loader will start and request administrator
echo privileges to update the bmod:// protocol registration.
echo.
echo After the mod loader opens, the GameBanana 1-click install
echo should work correctly.
echo.
pause



