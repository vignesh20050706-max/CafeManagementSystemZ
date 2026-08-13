@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0SetupGitHubSync.ps1"
if errorlevel 1 (
  echo.
  echo Setup stopped. Read the message above, resolve it, and run this file again.
  pause
)
endlocal

