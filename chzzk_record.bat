@echo off
echo Checking if python exists

REM Check for Python 3 and assign its path to a variable
where python3 >nul 2>&1
if %errorlevel% == 0 (
    set py=python3
    echo Using python3
) else (
    python --version 2>&1 | findstr "3." >nul
    if %errorlevel% == 0 (
        set py=python
        echo Using python
    ) else (
        echo Please install Python3 or 3.11 manually.
        exit /b 1
    )
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
"%VENV_DIR%\Scripts\python" chzzk_record.py

exit /b 0
