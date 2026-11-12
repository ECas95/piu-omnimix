cd "/d/Pump It Up Data/PIU"
P="final_v363/patch6"
python -B final_v363/build_catalog.py > $P/catalog.log 2>&1; echo CATALOG_RC $?
python -B final_v363/patch5_rise/run_harness.py > $P/harness.log 2>&1; echo HARNESS_RC $?; tail -1 $P/harness.log | cut -c1-300
python -B final_v363/runtime_merged17/compile_runtime.py > $P/runtime.log 2>&1; echo RUNTIME_RC $?; tail -1 $P/runtime.log | cut -c1-300
python -B $P/build_patch6.py > $P/build_patch6.log 2>&1; echo PATCH_RC $?; grep -v "^PACK " $P/build_patch6.log | tail -4 | cut -c1-900
echo ALL_DONE
