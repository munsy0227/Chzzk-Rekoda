@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

echo Check if uv is installed
where uv >nul 2>&1
if %errorlevel%==0 (
    echo Found uv.
) else (
    echo uv is not installed. Installing uv now...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = 3072; irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo Failed to install uv.
        pause
        exit /b 1
    )

    echo uv installation completed.
    echo Please close this window and rerun the script after installation is recognized.
    pause
    exit /b 0
)

echo Installing ffmpeg
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_ffmpeg_windows.ps1"
if errorlevel 1 (
    echo Failed to install ffmpeg.
    pause
    exit /b 1
)

echo Starting configuration
call "%~dp0settings.bat"
if errorlevel 1 (
    echo Settings script failed.
    pause
    exit /b 1
)

echo Configuration completed!
echo If you want to reconfigure, please run the "settings.bat" script directly
pause
exit /b 0
