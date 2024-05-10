chcp 65001
@echo off
setlocal EnableDelayedExpansion

echo Checking for an installed Python version...

REM Check for Python 3 and capture the version output
for /f "delims=" %%i in ('python --version 2^>^&1') do set pyversion=%%i

REM Check if the version string contains "Python 3"
echo !pyversion! | findstr /C:"Python 3" > nul
if %errorlevel% == 0 (
    echo Found installed Python: !pyversion!
    set py=python
) else (
    REM If Python 3 is not found, try finding python3 explicitly
    where python3 >nul 2>&1
    if %errorlevel% == 0 (
        set py=python3
        echo Using python3 as fallback
    ) else (
        echo Python 3 is not installed. Please install Python 3.
        exit /b 1
    )
)

echo Activating the virtual environment...
call venv\Scripts\activate

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

echo Executing the settings script...
!py! settings.py

echo Script execution completed.
exit /b 0


