@echo off
REM Launcher for Duplicate Question Detector GUI
REM Double-click this file to open the application

echo ========================================
echo   Detector de Preguntas Duplicadas
echo ========================================
echo.
echo Iniciando la aplicacion...
echo.

REM Try to run with python
python detectar_duplicados_gui.py

REM If that fails, try with py
if errorlevel 1 (
    py detectar_duplicados_gui.py
)

REM If still fails, show error
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo encontrar Python.
    echo Por favor, asegurate de tener Python instalado.
    echo.
    pause
)

