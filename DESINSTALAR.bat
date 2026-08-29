@echo off
setlocal
title Desinstalar Imagenes

set "APPNAME=Imagenes"
set "APPDIR=%LOCALAPPDATA%\%APPNAME%"

echo ============================================================
echo   DESINSTALADOR de %APPNAME%
echo ============================================================
echo Esto quitara los accesos directos, el PATH, el registro y la
echo carpeta:  %APPDIR%
echo.
choice /c SN /m "Seguro que quieres desinstalar"
if errorlevel 2 ( echo Cancelado. & pause & exit /b 0 )

echo.
echo - Quitando accesos directos y PATH...
if exist "%APPDIR%\accesos_path.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%APPDIR%\accesos_path.ps1" -Action uninstall -AppDir "%APPDIR%" -AppName "%APPNAME%"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0accesos_path.ps1" -Action uninstall -AppDir "%APPDIR%" -AppName "%APPNAME%"
)

echo - Quitando del registro (Agregar o quitar programas)...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APPNAME%" /f >nul 2>nul

echo - (Opcional) desinstalando el paquete pip si existe...
where python >nul 2>nul && python -m pip uninstall -y imagenes-cli >nul 2>nul
where py     >nul 2>nul && py -m pip uninstall -y imagenes-cli >nul 2>nul

echo - Borrando la carpeta de instalacion...
echo.
echo Desinstalacion completada. Puedes cerrar esta ventana.
if /i "%~dp0"=="%APPDIR%\" (
    start "" /min cmd /c "timeout /t 1 >nul & rmdir /s /q ""%APPDIR%"""
) else (
    rmdir /s /q "%APPDIR%" 2>nul
)
pause
endlocal
