@echo off
chcp 65001 >nul
title Autos Colombia - Instalacion
cd /d "%~dp0"
echo ========================================
echo   AUTOS COLOMBIA - INSTALACION
echo ========================================
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" seed.py
if errorlevel 1 goto error
echo.
echo Instalacion terminada. ANOTA LAS CLAVES mostradas arriba.
echo Despues ejecuta iniciar_windows.bat
pause
exit /b 0
:error
echo.
echo Ocurrio un error. Verifica que Python este instalado y tengas Internet.
pause
exit /b 1
