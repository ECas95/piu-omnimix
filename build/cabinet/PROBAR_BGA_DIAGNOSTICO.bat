@echo off
REM Diagnostico BGA Dark con teclado, SIN modificar el disco (capa temporal). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0probar_teclado.ps1" -Variant bga
pause
