@echo off
setlocal EnableDelayedExpansion

echo Check if uv is installed
REM Check if uv is installed
where uv >nul 2>&1
if %errorlevel%==0 (
    echo Found uv.
) else (
    echo uv is not installed. Installing uv now...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    echo uv installation completed.
    echo Please close this window and rerun the script after installation is recognized.
    pause
    exit /b 0
)

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

echo Downloading 7zr.exe
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.7-zip.org/a/7zr.exe', '7zr.exe')"

echo Downloading ffmpeg-release-full.7z
powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z', 'ffmpeg-release-full.7z')"

echo Extracting ffmpeg-release-full.7z
7zr x ffmpeg-release-full.7z -aoa

echo Finding the extracted ffmpeg directory
for /D %%A in (ffmpeg-*) do (
    if exist "ffmpeg" (
        echo Warning: "ffmpeg" directory already exists. Deleting existing "ffmpeg" directory.
        rmdir /s /q "ffmpeg"
        echo Renaming \"%%A\" to \"ffmpeg\"
        rename "%%A" "ffmpeg"
    ) else (
        echo Renaming \"%%A\" to \"ffmpeg\"
        rename "%%A" "ffmpeg"
    )
)

echo Starting configuration
REM Execute the settings script
call settings.bat
echo Configuration completed!
echo If you want to reconfigure, please run the \"settings.bat\" script directly

REM Pause execution to allow the user to read the output
pause

exit /b 0
