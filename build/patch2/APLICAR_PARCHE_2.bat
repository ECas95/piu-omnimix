@echo off
REM PARCHE 2: corrige el apagado al entrar a la seleccion de canciones en el MK9 (cursor sin inicializar). Ejecutar como administrador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\diag\swap.ps1" fix
pause
