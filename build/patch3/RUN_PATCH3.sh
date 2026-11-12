#!/bin/bash
# Waits for the variant F regeneration (final_generation_v362/vF_full_01.log), regenerates EZ2ON + SSS, builds patch 3.
# If the regeneration died, rerun it (it resumes: songs already done are skipped):
#   cd "D:/Pump It Up Data/PIU/final_generation_v362"; PIU_VARIANT=F python faithful.py --run vF_full_01 --registry FAITHFUL_REGISTRY.F.json
L='/d/Pump It Up Data/PIU/final_generation_v362/vF_full_01.log'
until grep -q FAITHFUL_FINISHED "$L";do sleep 120;done
cd '/d/Pump It Up Data/PIU/final_v363/patch3' && python regen_ez2_sss_F.py 11 > regen_ez2_sss_F.log 2>&1 && python build_patch3.py
