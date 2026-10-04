@echo off
rem Build TextFixer.exe and install it to %LOCALAPPDATA%\TextFixer\app
cd /d "%~dp0"
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -q -r requirements.txt -r requirements-build.txt || exit /b 1
.venv\Scripts\python tools\build.py
