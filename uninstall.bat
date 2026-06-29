@echo off
REM Remove chatxz install (.venv, bundled natives) and optionally app data on Windows.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo chatxz Windows Uninstall
echo ========================
echo.

echo [1/5] Stopping chatxz server and releasing ports...
call "%~dp0scripts\stop-chatxz.bat"
echo   Done.

echo [2/5] Removing Python environment and bundled voice libraries...
if exist ".venv" (
  rmdir /s /q ".venv"
  echo   Removed .venv
) else (
  echo   No .venv found
)
if exist "chatxz.egg-info" (
  rmdir /s /q "chatxz.egg-info"
  echo   Removed chatxz.egg-info
)
if exist "chatxz\core\native" (
  rmdir /s /q "chatxz\core\native"
  echo   Removed chatxz\core\native (downloaded libopus)
)
for %%F in (libopus.dll opus.dll libopus-0.dll) do (
  if exist "%%F" (
    del /f /q "%%F"
    echo   Removed %%F from repo root
  )
)
if exist ".voice-install.log" (
  del /f /q ".voice-install.log"
  echo   Removed .voice-install.log
)

echo [3/5] Application data (identity, settings, chat history)...
set "CONFIG_DIR=%USERPROFILE%\.config\chatxz"
set "DATA_DIR=%USERPROFILE%\.local\share\chatxz"
set "CACHE_DIR=%LOCALAPPDATA%\chatxz"
if defined CHATXZ_PORTABLE set "PORTABLE_DIR=%CHATXZ_PORTABLE%\chatxz-data"
if not defined PORTABLE_DIR if exist "chatxz-data" set "PORTABLE_DIR=%CD%\chatxz-data"

if exist "%CONFIG_DIR%" (
  echo   Config: %CONFIG_DIR%
  set /p RM1=   Remove config? [y/N]:
  if /I "!RM1!"=="y" rmdir /s /q "%CONFIG_DIR%" && echo   Removed config.
)
if exist "%DATA_DIR%" (
  echo   Data: %DATA_DIR%
  set /p RM2=   Remove data? [y/N]:
  if /I "!RM2!"=="y" rmdir /s /q "%DATA_DIR%" && echo   Removed data.
)
if exist "%CACHE_DIR%" (
  echo   Cache: %CACHE_DIR%
  set /p RM4=   Remove cache? [y/N]:
  if /I "!RM4!"=="y" rmdir /s /q "%CACHE_DIR%" && echo   Removed cache.
)
if defined PORTABLE_DIR if exist "!PORTABLE_DIR!" (
  echo   Portable: !PORTABLE_DIR!
  set /p RM3=   Remove portable data? [y/N]:
  if /I "!RM3!"=="y" rmdir /s /q "!PORTABLE_DIR!" && echo   Removed portable data.
)

echo [4/4] Cleanup complete.
echo.
echo To run again:  run.bat web --share
echo.
endlocal
exit /b 0