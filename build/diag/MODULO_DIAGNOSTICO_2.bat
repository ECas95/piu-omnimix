@echo off
REM Pone el modulo de DIAGNOSTICO 3 (graba en /SETTINGS/PIU/diag.log, sobrevive al apagado). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0swap.ps1" diag2
pause
