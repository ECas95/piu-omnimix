@echo off
REM Parche 1 sobre el disco del cabinet (v379): agrega las canciones nuevas de EZ2ON. Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0aplicar_parche.ps1"
pause
