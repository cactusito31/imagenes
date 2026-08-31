@echo off
title Respaldar imagenes-app
cd /d "%~dp0"
set "DEST=%USERPROFILE%\OneDrive - nbGroup Soluciones de Negocio\respaldos-git"

echo Guardando todo el historial del repositorio en:
echo   %DEST%
echo.
if not exist "%DEST%" mkdir "%DEST%"
git bundle create "%DEST%\imagenes-app.bundle" --all
if errorlevel 1 (
    echo [ERROR] No se ha podido crear el respaldo.
    pause
    exit /b 1
)
echo.
echo Listo. Para recuperarlo en otro equipo:
echo   git clone "%DEST%\imagenes-app.bundle" imagenes-app
echo.
echo (Esto se hace solo despues de cada commit; el .bat es por si acaso.)
pause
