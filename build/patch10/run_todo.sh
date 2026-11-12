# Patch 10 chain, after the conversion and the corrected IIDX media: selection, media of the new songs, UI, catalog, native validation, real order, Basic Mode, modules, archives. Stops at the first failure.
stop(){ echo "STOP_$1";echo RUN_TODO_DONE;exit 1; }
cd /d/PIU_NUEVAS;python -B seleccion_nuevas.py > seleccion.log 2>&1;tail -3 seleccion.log | cut -c1-300;grep -q NUEVAS_SELECTION seleccion.log || stop SELECCION
cd /d/PIU_INFINITY/channels;python prepare_media.py --workers 8 --songs $(cat /d/PIU_NUEVAS/selection_ids.txt) > media_nuevas.log 2>&1;grep -E "MEDIA_FINISHED" media_nuevas.log | cut -c1-200;grep -E "MEDIA_ERROR" media_nuevas.log | cut -c1-300 | head;grep -q "errors 0" media_nuevas.log || stop MEDIA
cd "/d/Pump It Up Data/PIU";P=final_v363/patch10
python -B final_v363/infinity/build_ui.py > $P/ui.log 2>&1;echo UI_RC $?;tail -1 $P/ui.log | cut -c1-200;grep -q INFINITY_UI_PREPARED $P/ui.log || stop UI
python -B final_v363/build_catalog.py > $P/catalog.log 2>&1;echo CATALOG_RC $?;tail -1 $P/catalog.log | cut -c1-300
python -B final_v363/patch5_rise/run_harness.py > $P/harness.log 2>&1;echo HARNESS_RC $?;tail -1 $P/harness.log | cut -c1-300;grep -q "MERGED17_NATIVE_FILTER PASS" $P/harness.log || stop HARNESS
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -u root -- bash "/mnt/d/Pump It Up Data/PIU/final_v363/patch8/orden_canales.sh" ../patch10/full_mode.txt > $P/orden.log 2>&1;echo DUMP_RC $?;tail -1 $P/orden.log | cut -c1-200
python -B $P/verificar_orden.py $P/full_mode.txt > $P/verificar_orden.log 2>&1;rc=$?;echo ORDER_RC $rc;cut -c1-120 $P/verificar_orden.log;[ $rc = 0 ] || stop ORDER
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -u root -- bash "/mnt/d/Pump It Up Data/PIU/final_v363/patch8/verificar_basic.sh" > $P/verificar_basic.log 2>&1;rc=$?;echo BASIC_RC $rc;tail -1 $P/verificar_basic.log | cut -c1-200;[ $rc = 0 ] || stop BASIC
python -B final_v363/runtime_merged17/compile_runtime.py > $P/runtime.log 2>&1;rc=$?;echo RUNTIME_RC $rc;tail -1 $P/runtime.log | cut -c1-300;[ $rc = 0 ] || stop RUNTIME
python -B $P/build_patch10.py > $P/build_patch10.log 2>&1;rc=$?;echo PATCH_RC $rc;grep -v "^PACK " $P/build_patch10.log | tail -5 | cut -c1-600;[ $rc = 0 ] || stop PATCH
python -B $P/crear_aplicar.py
echo RUN_TODO_DONE
