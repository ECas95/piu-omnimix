# Chain after the first conversion pass: retry failed songs, selection + banners, media, UI, catalog, native validation, modules, patch 7.
cd "/d/Pump It Up Data/PIU";P=final_v363/patch7
python -B final_v363/infinity/build_ui.py > $P/ui.log 2>&1;echo UI_RC $?;tail -1 $P/ui.log | cut -c1-200
python -B final_v363/build_catalog.py > $P/catalog.log 2>&1;echo CATALOG_RC $?;tail -2 $P/catalog.log | cut -c1-300
python -B final_v363/patch5_rise/run_harness.py > $P/harness.log 2>&1;echo HARNESS_RC $?;tail -1 $P/harness.log | cut -c1-300
python -B final_v363/runtime_merged17/compile_runtime.py > $P/runtime.log 2>&1;echo RUNTIME_RC $?;tail -1 $P/runtime.log | cut -c1-300
python -B $P/build_patch7.py > $P/build_patch7.log 2>&1;echo PATCH_RC $?;grep -v "^PACK " $P/build_patch7.log | tail -5 | cut -c1-500
echo RUN_TODO_DONE
