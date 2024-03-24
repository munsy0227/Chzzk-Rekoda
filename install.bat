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
    echo Python 3 is not installed. Please install Python 3.
    exit /b 1
)

REM Check if the "plugin" directory exists and create it if it doesn't
if not exist ".\plugin\" mkdir ".\plugin"

echo Checking for the chzzk.py plugin...

REM Calculate the checksum of the existing file if it exists
if exist ".\plugin\chzzk.py" (
    powershell -Command "$current = (Get-FileHash .\plugin\chzzk.py -Algorithm MD5).Hash; $remote = (Invoke-WebRequest -Uri https://raw.githubusercontent.com/fml09/streamlink/c29ab4040b56511b4fd4915954b8b0796b72ad40/src/streamlink/plugins/chzzk.py -UseBasicParsing | Get-FileHash -Algorithm MD5).Hash; if ($current -ne $remote) { Write-Output 'different' } else { Write-Output 'same' }" > checksum.txt
    set /p filestatus=<checksum.txt
    if "!filestatus!"=="different" (
        echo Existing chzzk.py plugin is outdated. Updating...
        powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/fml09/streamlink/c29ab4040b56511b4fd4915954b8b0796b72ad40/src/streamlink/plugins/chzzk.py -OutFile .\plugin\chzzk.py"
    ) else (
        echo Existing chzzk.py plugin is up-to-date.
    )
) else (
    echo Downloading chzzk.py plugin...
    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/fml09/streamlink/c29ab4040b56511b4fd4915954b8b0796b72ad40/src/streamlink/plugins/chzzk.py -OutFile .\plugin\chzzk.py"
)

REM Delete the checksum file if it exists
if exist checksum.txt del checksum.txt

echo Installing required components
REM Create a virtual environment in the current directory
!py! -m venv venv

REM Dynamically get the current directory's virtual environment activation script
set VENV_DIR=%CD%\venv
if exist "!VENV_DIR!" (
    echo Activating virtual environment in !VENV_DIR!
    call "!VENV_DIR!\Scripts\activate"
) else (
    echo Virtual environment not found in !VENV_DIR!
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

REM Pause execution to allow the user to read the output
pause

exit /b 0
