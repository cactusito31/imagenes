@echo off
setlocal enabledelayedexpansion
title Crear imagenes.exe
cd /d "%~dp0"

echo ============================================================
echo   GENERADOR DE imagenes.exe
echo ============================================================
echo.

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
    echo [ERROR] No se ha encontrado Python.
    echo Instalalo desde https://www.python.org/downloads/  ^(marca "Add to PATH"^).
    pause
    exit /b 1
)
echo Usando Python: %PY%
echo.

echo [1/4] Instalando dependencias...
%PY% -m pip install --user --upgrade pip >nul 2>nul
%PY% -m pip install --user -r requirements.txt
if errorlevel 1 (
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
)
echo.

echo [2/4] Pasando las pruebas...
%PY% -m pytest tests -q
if errorlevel 1 (
    echo.
    echo [AVISO] Hay pruebas que fallan.
    choice /c SN /m "Compilar de todas formas"
    if errorlevel 2 exit /b 1
)
echo.

echo [3/4] Compilando el ejecutable...
%PY% -m PyInstaller --clean --noconfirm imagenes.spec
if errorlevel 1 (
    echo [ERROR] Fallo la compilacion.
    pause
    exit /b 1
)
echo.

echo [4/4] Listo:  "%~dp0dist\imagenes.exe"
echo.
echo Ahora puedes ejecutar INSTALAR.bat para instalarlo en este equipo,
echo o copiar dist\imagenes.exe a cualquier PC Windows.
echo.
pause
