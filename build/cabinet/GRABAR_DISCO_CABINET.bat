@echo off
REM PIU omnimix v379 - graba la imagen de gabinete (MK9 original) en el disco de 1 TB y la verifica.
REM Clic derecho > Ejecutar como administrador. Necesita el disco E: conectado.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0grabar_disco.ps1"
pause
