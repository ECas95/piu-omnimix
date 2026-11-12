@echo off
REM Prueba en QEMU con teclado simulando el MK9 (PIUIO sin placa de botones). No modifica el disco. Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0probar_teclado.ps1" fx
pause
