@echo off
setlocal
chcp 65001 >nul
title Autos Colombia - Pruebas funcionales
cd /d "%~dp0"
echo ===============================================
echo   AUTOS COLOMBIA - VALIDACION AUTOMATICA
echo ===============================================
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Primero ejecuta instalar_windows.bat
    pause
    exit /b 1
)
echo.
echo Instalando pytest si es necesario...
".venv\Scripts\python.exe" -m pip install "pytest>=8,<10"
if errorlevel 1 goto error
echo.
echo Ejecutando pruebas Python, SQLite, rutas Flask y respaldo...
".venv\Scripts\python.exe" -m pytest tests -v --tb=short
if errorlevel 1 goto error
echo.
echo PRUEBAS AUTOMATICAS APROBADAS.
echo Tambien verifica las pantallas en Chrome y Edge,
echo y descarga/restaura una copia SQLite en Windows.
pause
exit /b 0
:error
echo.
echo ALGUNA PRUEBA FALLO O NO FUE POSIBLE INSTALAR DEPENDENCIAS.
echo Guarda una captura y revisa el error antes de entregar.
pause
exit /b 1
