@echo off
REM Vuelve a poner el modulo de gabinete del parche 1. Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0swap.ps1" restore
pause
