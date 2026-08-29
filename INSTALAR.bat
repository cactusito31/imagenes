@echo off
setlocal enabledelayedexpansion
title Instalar Imagenes
cd /d "%~dp0"

set "APPNAME=Imagenes"
set "APPDIR=%LOCALAPPDATA%\%APPNAME%"

echo ============================================================
echo   INSTALADOR de %APPNAME%
echo ============================================================
echo.

rem --- Localizar el ejecutable: al lado del .bat o en dist\ ---
set "EXE="
if exist "%~dp0imagenes.exe"      set "EXE=%~dp0imagenes.exe"
if not defined EXE if exist "%~dp0dist\imagenes.exe" set "EXE=%~dp0dist\imagenes.exe"
if not defined EXE (
    echo [ERROR] No se encuentra imagenes.exe.
    echo Ejecuta antes CREAR_EXE.bat, o pon este .bat junto al ejecutable.
    echo.
    pause
    exit /b 1
)
echo Ejecutable: %EXE%
echo Destino   : %APPDIR%
echo.

if "%LOCALAPPDATA%"=="" (
    echo [ERROR] La variable LOCALAPPDATA esta vacia. Abortado por seguridad.
    pause
    exit /b 1
)

echo - Copiando archivos...
if not exist "%APPDIR%" mkdir "%APPDIR%"
copy /y "%EXE%" "%APPDIR%\imagenes.exe" >nul
if errorlevel 1 (
    echo [ERROR] No se ha podido copiar el ejecutable.
    echo Si la aplicacion esta abierta, cierrala y vuelve a intentarlo.
    pause
    exit /b 1
)
if exist "%~dp0imagenes.ico"       copy /y "%~dp0imagenes.ico"       "%APPDIR%\" >nul
if exist "%~dp0accesos_path.ps1"   copy /y "%~dp0accesos_path.ps1"   "%APPDIR%\" >nul
if exist "%~dp0DESINSTALAR.bat"    copy /y "%~dp0DESINSTALAR.bat"    "%APPDIR%\" >nul
if exist "%~dp0LEEME.txt"          copy /y "%~dp0LEEME.txt"          "%APPDIR%\" >nul

rem --- Version, para "Agregar o quitar programas" ---
set "VER="
for /f "usebackq delims=" %%v in (`"%APPDIR%\imagenes.exe" --version 2^>nul`) do set "VER=%%v"
if not defined VER set "VER=2.0.0"

echo - Creando accesos directos, menu contextual y PATH...
set "ICO=%APPDIR%\imagenes.exe"
if exist "%APPDIR%\imagenes.ico" set "ICO=%APPDIR%\imagenes.ico"
powershell -NoProfile -ExecutionPolicy Bypass -File "%APPDIR%\accesos_path.ps1" ^
  -Action install -AppDir "%APPDIR%" -AppName "%APPNAME%" -Icon "%ICO%" -Version "%VER%"
if errorlevel 1 (
    echo [AVISO] Los archivos estan instalados, pero fallo la integracion con Windows.
)

echo.
echo ============================================================
echo   Instalado.  %VER%
echo ============================================================
echo   Puedes usarlo de cuatro maneras:
echo     - doble clic en el acceso del Escritorio
echo     - arrastrando una carpeta sobre el acceso
echo     - clic derecho sobre una carpeta ^> Convertir imagenes
echo     - escribiendo  imagenes  en cualquier terminal NUEVA
echo.
echo   Ayuda:  imagenes --help
echo.
pause
endlocal
