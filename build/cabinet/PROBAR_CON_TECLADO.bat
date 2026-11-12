@echo off
REM Prueba el disco del cabinet en QEMU con teclado, SIN modificar el disco (capa temporal). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0probar_teclado.ps1"
pause
