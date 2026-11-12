@echo off
REM Prueba el disco del cabinet ya grabado en QEMU (modo snapshot: no escribe el disco).
REM Clic derecho > Ejecutar como administrador, con el disco del MK9 conectado.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0probar_disco.ps1"
pause
