cd "/d/Pump It Up Data/PIU"
P="final_v363/patch5_rise"
python -B final_v363/build_catalog.py > $P/catalog.log 2>&1; echo CATALOG_RC $?
python -B $P/run_harness.py > $P/harness.log 2>&1; echo HARNESS_RC $?; tail -2 $P/harness.log | cut -c1-300
python -B final_v363/runtime_merged17/compile_runtime.py > $P/runtime.log 2>&1; echo RUNTIME_RC $?; tail -2 $P/runtime.log | cut -c1-300
echo ALL_DONE
