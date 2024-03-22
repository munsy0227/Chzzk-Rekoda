@echo off
setlocal EnableDelayedExpansion

echo Checking if Python exists

REM Check for Python 3 and assign its path to a variable
where python3 >nul 2>&1
if %errorlevel% == 0 (
    set py=python3
    echo Using python3
) else (
    python --version 2>&1 | findstr /R "3." >nul
    if %errorlevel% == 0 (
        set py=python
        echo Using python
    ) else (
        echo Please install Python3 or 3.11 manually.
        exit /b 1
    )
)

echo Installing required components
REM Create a virtual environment in the current directory
%py% -m venv venv

REM Dynamically get the current directory's virtual environment activation script
set VENV_DIR=%CD%\venv
if exist "%VENV_DIR%" (
    echo Activating virtual environment in %VENV_DIR%
    call "%VENV_DIR%\Scripts\activate"
) else (
    echo Virtual environment not found in %VENV_DIR%
    exit /b 1
)

REM Install required Python packages
"%VENV_DIR%\Scripts\pip" install --upgrade streamlink aiohttp aiofiles orjson

REM Deactivate the virtual environment
call "%VENV_DIR%\Scripts\deactivate"
echo Required components installation completed!

echo Downloading 7zr.exe
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.7-zip.org/a/7zr.exe', '7zr.exe')"

echo Downloading ffmpeg-release-full.7z
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z', 'ffmpeg-release-full.7z')"

echo Extracting ffmpeg-release-full.7z
7zr x ffmpeg-release-full.7z -aoa

echo Finding the extracted ffmpeg directory
for /D %%A in (ffmpeg-*) do (
    if exist "ffmpeg" (
        echo Warning: "ffmpeg" directory already exists, not renaming "%%A".
    ) else (
        echo Renaming "%%A" to "ffmpeg"
        rename "%%A" "ffmpeg"
    )
)

echo Starting configuration
REM Execute the settings script
call settings.bat
echo Configuration completed!
echo If you want to reconfigure, please run the "settings.bat" script directly

exit /b 0
