@echo off
setlocal
title Desinstalar Imagenes

set "APPNAME=Imagenes"
set "APPDIR=%LOCALAPPDATA%\%APPNAME%"
set "CFGDIR=%APPDATA%\%APPNAME%"

if "%LOCALAPPDATA%"=="" (
    echo [ERROR] La variable LOCALAPPDATA esta vacia. Abortado por seguridad.
    pause
    exit /b 1
)

echo ============================================================
echo   DESINSTALADOR de %APPNAME%
echo ============================================================
echo Se quitaran los accesos directos, el menu contextual, el PATH,
echo el registro y la carpeta:
echo   %APPDIR%
echo.
choice /c SN /m "Seguro que quieres desinstalar"
if errorlevel 2 ( echo Cancelado. & pause & exit /b 0 )

echo.
echo - Quitando accesos directos, menu contextual, registro y PATH...
if exist "%APPDIR%\accesos_path.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%APPDIR%\accesos_path.ps1" -Action uninstall -AppDir "%APPDIR%" -AppName "%APPNAME%"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0accesos_path.ps1" -Action uninstall -AppDir "%APPDIR%" -AppName "%APPNAME%"
)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APPNAME%" /f >nul 2>nul

echo.
echo Tus presets y la ultima configuracion estan en:
echo   %CFGDIR%
choice /c SN /m "Quieres borrarlos tambien"
if errorlevel 2 (
    echo   Se conservan.
) else (
    if not "%APPDATA%"=="" if exist "%CFGDIR%" rmdir /s /q "%CFGDIR%" 2>nul
    echo   Borrados.
)

echo.
echo - Borrando la carpeta de instalacion...
echo.
echo Desinstalacion completada. Puedes cerrar esta ventana.
rem El .bat se esta ejecutando desde dentro de la carpeta que hay que borrar:
rem se lanza un proceso aparte que espera a que este termine.
if /i "%~dp0"=="%APPDIR%\" (
    start "" /min cmd /c "timeout /t 1 >nul & rmdir /s /q ""%APPDIR%"""
) else (
    rmdir /s /q "%APPDIR%" 2>nul
)
pause
endlocal
