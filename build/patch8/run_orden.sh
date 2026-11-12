# Second part of patch 8: module with the title order, native validation, real lists against the baseline, patch rebuilt. Stops at the first failure.
cd "/d/Pump It Up Data/PIU";P=final_v363/patch8
stop(){ echo "STOP_$1";echo RUN_ORDEN_DONE;exit 1; }
python -B $P/aplicar_orden.py || stop EDIT
python -B final_v363/patch5_rise/run_harness.py > $P/harness2.log 2>&1;rc=$?;echo HARNESS_RC $rc;tail -1 $P/harness2.log | cut -c1-300;grep -q "MERGED17_NATIVE_FILTER PASS" $P/harness2.log || stop HARNESS
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -u root -- bash "/mnt/d/Pump It Up Data/PIU/final_v363/patch8/orden_canales.sh" full_despues.txt > $P/orden.log 2>&1;echo DUMP_RC $?;tail -1 $P/orden.log | cut -c1-200
python -B $P/verificar_orden.py > $P/verificar_orden.log 2>&1;rc=$?;echo ORDER_RC $rc;cat $P/verificar_orden.log | cut -c1-150;[ $rc = 0 ] || stop ORDER
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -u root -- bash "/mnt/d/Pump It Up Data/PIU/final_v363/patch8/verificar_basic.sh" > $P/verificar.log 2>&1;rc=$?;echo BASIC_RC $rc;tail -1 $P/verificar.log | cut -c1-200;[ $rc = 0 ] || stop BASIC
python -B final_v363/runtime_merged17/compile_runtime.py > $P/runtime.log 2>&1;rc=$?;echo RUNTIME_RC $rc;tail -1 $P/runtime.log | cut -c1-300;[ $rc = 0 ] || stop RUNTIME
python -B $P/build_patch8.py > $P/build_patch8.log 2>&1;rc=$?;echo PATCH_RC $rc;grep -v "^PACK " $P/build_patch8.log | tail -3 | cut -c1-900;[ $rc = 0 ] || stop PATCH
python -B $P/crear_aplicar.py;sed -n 2,3p $P/aplicar.sh | cut -c1-170
echo RUN_ORDEN_DONE
