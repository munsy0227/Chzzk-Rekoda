@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

REM Execute your Python script
uv run chzzk_record.py
if errorlevel 1 (
    echo Recorder exited with an error.
    exit /b 1
)

exit /b 0
