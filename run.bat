@echo off
rem Change to the directory of this script
cd /d "%~dp0"

rem Set UTF-8 encoding for the Windows console to support emoji printing
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

rem Activate the Python virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

rem Run the main application with UTF-8 mode forced
python -X utf8 python_fmg/main.py

pause
