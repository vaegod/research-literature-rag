@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_app.ps1" -Port 8010
if errorlevel 1 (
  echo.
  echo Failed to start. Press any key to close.
  pause >nul
)

