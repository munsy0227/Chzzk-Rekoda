@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

echo Executing the settings script...
uv run settings.py
if errorlevel 1 (
    echo Settings script failed.
    exit /b 1
)

echo Script execution completed.
exit /b 0
