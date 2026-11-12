@echo off
REM Copia los logs del disco del cabinet a la PC, SIN modificar el disco (montaje de solo lectura). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0leer_logs.ps1"
pause
