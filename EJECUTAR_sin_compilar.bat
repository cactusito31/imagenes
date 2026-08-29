@echo off
title Imagenes (sin compilar)
cd /d "%~dp0"
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
    echo [ERROR] No se ha encontrado Python. Instalalo desde python.org
    echo y marca la casilla "Add python.exe to PATH".
    pause
    exit /b 1
)
%PY% -c "import PIL" 2>nul || %PY% -m pip install --user Pillow
%PY% imagenes.py %*
pause
