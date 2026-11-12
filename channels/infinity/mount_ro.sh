#!/bin/bash
L=$(losetup -j /mnt/d/PIU_INFINITY/piu-inf10th-v1.2h.img | cut -d: -f1 | head -1)
[ -z "$L" ] && L=$(losetup -f --show -r -P /mnt/d/PIU_INFINITY/piu-inf10th-v1.2h.img)
echo $L; blkid ${L}p1 ${L}p2 ${L}p3
for p in 1 2 3; do mkdir -p /mnt/inf$p; mountpoint -q /mnt/inf$p || mount -o ro,noload ${L}p$p /mnt/inf$p || mount -o ro ${L}p$p /mnt/inf$p; done
df -h /mnt/inf1 /mnt/inf2 /mnt/inf3
for p in 1 2 3; do echo "== inf$p"; ls /mnt/inf$p; done
