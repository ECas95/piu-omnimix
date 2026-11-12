# Patch 8 chain: rebuild the catalog, native validation, Basic Mode against the official catalog, then the archive. Stops at the first failure.
cd "/d/Pump It Up Data/PIU";P=final_v363/patch8;S="$1"
python -B $P/preparar.py "$S" || { echo STOP_PREPARAR;echo RUN_ALL_DONE;exit 1; }
python -B final_v363/build_catalog.py > $P/catalog.log 2>&1;echo CATALOG_RC $?;tail -1 $P/catalog.log | cut -c1-300
python -B final_v363/patch5_rise/run_harness.py > $P/harness.log 2>&1;rc=$?;echo HARNESS_RC $rc;tail -1 $P/harness.log | cut -c1-300;[ $rc = 0 ] && grep -q "MERGED17_NATIVE_FILTER PASS" $P/harness.log || { echo STOP_HARNESS;echo RUN_ALL_DONE;exit 1; }
for k in cabinet trial;do cmp final_v363/runtime_merged17/${k}_runtime_source/anime_title_order.h $P/respaldo_antes/${k}_runtime_source__anime_title_order.h && echo "TITLE_TABLE_SAME $k" || { echo STOP_TITLE_TABLE;echo RUN_ALL_DONE;exit 1; };done
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -u root -- bash "/mnt/d/Pump It Up Data/PIU/final_v363/patch8/verificar_basic.sh" > $P/verificar.log 2>&1;rc=$?;echo VERIFY_RC $rc;tail -4 $P/verificar.log | cut -c1-200;[ $rc = 0 ] || { echo STOP_VERIFY;echo RUN_ALL_DONE;exit 1; }
python -B $P/build_patch8.py > $P/build_patch8.log 2>&1;echo PATCH_RC $?;grep -v "^PACK " $P/build_patch8.log | tail -4 | cut -c1-500
echo RUN_ALL_DONE
