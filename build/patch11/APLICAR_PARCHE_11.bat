@echo off
REM PARCHE 11: arregla los hexagonos de canal (los 4 IIDX comparten uno; vuelven los numeros del recuadro de descripcion). Requiere el parche 10. Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0aplicar.ps1"
pause
