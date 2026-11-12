@echo off
REM Prueba en QEMU como un MK9 con 1 GB de RAM (no modifica el disco). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0probar_teclado.ps1" fx 1024
pause
