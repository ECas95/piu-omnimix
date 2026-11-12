@echo off
REM Regenera (o reanuda) los charts custom con la variante F (incluye EZ2ON y SSS) y luego construye el parche 3. No toca el disco del cabinet.
cd /d "D:\Pump It Up Data\PIU\final_generation_v362"
set PIU_VARIANT=F
python faithful.py --run vF_full_01 --registry FAITHFUL_REGISTRY.F.json
cd /d "%~dp0"
python regen_ez2_sss_F.py 11
python build_patch3.py
pause
