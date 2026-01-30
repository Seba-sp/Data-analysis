@echo off
python launcher.py
if %errorlevel% neq 0 (
    echo.
    echo Error executing launcher.py. Please check if Python is installed and added to PATH.
    pause
)
