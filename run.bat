@echo off
rem Change to the directory of this script
cd /d "%~dp0"

rem Activate the Python virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

rem Run the main application
python python_fmg/main.py

pause
