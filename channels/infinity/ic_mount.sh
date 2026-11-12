F='/mnt/e/Pump It Up Data/imagen_original/imperfect_collection.v1_3_1.img/imperfect_collection.v1_3_1.img'
mkdir -p /mnt/ic_boot /mnt/ic_set
mountpoint -q /mnt/ic_boot || mount -o ro,loop,offset=$((17321984*512)),sizelimit=$((102400*512)) "$F" /mnt/ic_boot
mountpoint -q /mnt/ic_set || mount -o ro,loop,offset=$((1000000*512)),sizelimit=$((16321984*512)) "$F" /mnt/ic_set
echo "== BOOT"; ls -la /mnt/ic_boot /mnt/ic_boot/* 2>/dev/null | head -40
echo "== SETTINGS"; ls -la /mnt/ic_set | head -40
