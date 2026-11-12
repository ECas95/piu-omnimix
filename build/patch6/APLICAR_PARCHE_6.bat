@echo off
REM PARCHE 6: quita del canal EZ2DANCER las 35 canciones del paquete EZ2 series. Requiere el parche 5. Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0aplicar.ps1"
pause
