@echo off
REM Pone el modulo de DIAGNOSTICO (registra la causa exacta si el juego falla). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0swap.ps1" diag
pause
