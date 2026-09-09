@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUTF8=1
start "" wscript.exe //nologo "%~dp0chzzk_gui.vbs" %*
exit /b %errorlevel%
