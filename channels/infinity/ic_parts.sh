F='/mnt/e/Pump It Up Data/imagen_original/imperfect_collection.v1_3_1.img/imperfect_collection.v1_3_1.img'
fdisk -l "$F" 2>&1 | head -20
for o in $(fdisk -l -o Start "$F" 2>/dev/null | grep -E '^ *[0-9]+$'); do dd if="$F" bs=512 skip=$o count=8 2>/dev/null | file -; done
