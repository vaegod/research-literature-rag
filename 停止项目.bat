@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_app.ps1" -Port 8010
echo.
echo Done. Press any key to close.
pause >nul

