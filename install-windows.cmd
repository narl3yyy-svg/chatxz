@echo off
REM Optional setup (voice extras). To run the server:  run.cmd web --share
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-windows.ps1" %*
exit /b %ERRORLEVEL%