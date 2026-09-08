@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUTF8=1
uv run --extra gui chzzk_gui.py %*
exit /b %errorlevel%
