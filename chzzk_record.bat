@echo off
echo Checking for an installed Python version...

REM Check for Python 3 and capture the version output
for /f "delims=" %%i in ('python --version 2^>^&1') do set pyversion=%%i

REM Check if the version string contains "Python 3"
echo %pyversion% | findstr /C:"Python 3" > nul
if %errorlevel% == 0 (
    echo Found installed Python: %pyversion%
) else (
    echo Python 3 is not installed. Please install Python 3.
    exit /b 1
)

REM Detect the current directory and activate the virtual environment
set VENV_DIR=%CD%\venv
if exist "%VENV_DIR%" (
    echo Activating virtual environment in %VENV_DIR%
    call "%VENV_DIR%\Scripts\activate"
) else (
    echo Virtual environment not found in %VENV_DIR%
    exit /b 1
)

REM Execute your Python script
python chzzk_record.py

exit /b 0
