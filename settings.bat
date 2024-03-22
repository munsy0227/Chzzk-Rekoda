@echo off
echo Checking if python exists

REM Trying to find python3 first
where python3 >nul 2>&1
if %errorlevel% == 0 (
    set py=python3
    echo Using python3
) else (
    REM Falling back to python if python3 is not found
    python --version 2>nul | findstr /R "3." >nul
    if %errorlevel% == 0 (
        set py=python
        echo Using python
    ) else (
        echo Please install Python3 or 3.11 manually.
        exit /b 1
    )
)

call venv\Scripts\activate
%py% settings.py

exit /b 0

