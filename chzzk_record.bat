@echo off

REM Set the environment variable to force UTF-8 encoding
set PYTHONUTF8=1

REM Execute your Python script
uv run chzzk_record.py

exit /b 0
