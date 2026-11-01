@echo off
title Nexus Trade AI
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
  echo During setup, tick "Add Python to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Starting Nexus Trade AI at http://127.0.0.1:5000
start "" http://127.0.0.1:5000
python app.py
pause
