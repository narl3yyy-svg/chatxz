@echo off
REM chatxz on Windows — same as ./run.sh on Linux/macOS.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
exit /b %ERRORLEVEL%