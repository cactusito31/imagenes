@echo off
setlocal enabledelayedexpansion
title Crear imagenes.exe
cd /d "%~dp0"

echo ============================================================
echo   GENERADOR DE imagenes.exe
echo   (esto solo hay que hacerlo UNA vez, en un PC con Python)
echo ============================================================
echo.

rem --- Detectar Python (python o py) ---
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
    echo [ERROR] No se ha encontrado Python.
    echo Instalalo desde https://www.python.org/downloads/  ^(marca "Add to PATH"^).
    echo.
    pause
    exit /b 1
)
echo Usando Python: %PY%
echo.

echo [1/3] Instalando herramientas (Pillow y PyInstaller)...
%PY% -m pip install --user --upgrade pip >nul
%PY% -m pip install --user Pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] No se pudieron instalar las herramientas.
    pause
    exit /b 1
)
echo.

echo [2/3] Compilando el ejecutable...
%PY% -m PyInstaller --onefile --console --name imagenes --clean imagenes.py
if errorlevel 1 (
    echo [ERROR] Fallo la compilacion.
    pause
    exit /b 1
)
echo.

echo [3/3] Listo.
echo El ejecutable esta en:  "%~dp0dist\imagenes.exe"
echo Copia ese unico archivo a cualquier PC Windows y ejecutalo con doble clic
echo o desde la terminal escribiendo:  imagenes
echo.
echo (Puedes borrar las carpetas build y __pycache__ y el archivo imagenes.spec)
echo.
pause
