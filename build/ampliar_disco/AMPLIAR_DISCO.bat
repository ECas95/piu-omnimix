@echo off
REM Amplia la particion del juego con el espacio libre al final del disco. Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0aplicar.ps1"
pause
