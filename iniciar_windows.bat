@echo off
chcp 65001 >nul
title Autos Colombia - Servidor Local
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ejecuta primero instalar_windows.bat
    pause
    exit /b 1
)
echo Abre http://127.0.0.1:5000 en tu navegador.
echo Manten esta ventana abierta mientras uses el sistema.
".venv\Scripts\python.exe" run.py
pause
