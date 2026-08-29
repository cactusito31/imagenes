@echo off
title imagenes
cd /d "%~dp0"
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
    pause & exit /b 1
)
%PY% -m pip install --user Pillow >nul 2>nul
%PY% imagenes.py
pause
