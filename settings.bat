@echo off
setlocal EnableDelayedExpansion

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

echo Executing the settings script...
uv run settings.py

echo Script execution completed.
exit /b 0


