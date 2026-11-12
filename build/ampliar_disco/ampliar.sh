#!/bin/bash
# Grows the game partition (3) of the cabinet disk over the unallocated space at the end of the disk. Partitions 1 and 2 and every file stay
# where they are; only partition 3's end moves. Saves the old table first and stops if the layout is not the expected one.
# usage: ampliar.sh [device]  (no device: found by the game's partition UUID, attached with wsl --mount --bare)
set -euo pipefail
P3UUID=50e2dd64-0be5-4e57-8cc1-284d1201369f;out='/mnt/d/Pump It Up Data/PIU/final_v363/ampliar_disco'
if [ $# -ge 1 ];then disk=$1;part=${2:-${disk}p3}
else
  udevadm settle;part=$(readlink -f /dev/disk/by-uuid/$P3UUID);test -b "$part" || { echo 'No es el disco del cabinet';exit 1; }
  disk=/dev/$(lsblk -no pkname "$part")
fi
! grep -q "^$part " /proc/mounts || { echo "$part esta montada";exit 1; }
sfdisk -d "$disk" > "$out/tabla_antes.txt";cat "$out/tabla_antes.txt"
test "$(sfdisk -d "$disk" | grep -c '^/dev\|^[^ ]*p\?[0-9] :')" -ge 3
test "$(sfdisk -d "$disk" | sed -n 's/^label: //p')" = dos || { echo 'La tabla no es MBR: no toco nada';exit 1; }
test "$(sfdisk -l -o Device "$disk" | grep -c "^$disk")" = 3 || { echo 'El disco no tiene exactamente 3 particiones: no toco nada';exit 1; }
e2fsck -f -y "$part" || test $? -le 1
before=$(dumpe2fs -h "$part" 2>/dev/null | awk -F: '/^Block count/{print $2+0}')
echo ', +' | sfdisk --no-reread --no-tell-kernel -N 3 "$disk"
blockdev --rereadpt "$disk" || partprobe "$disk" || true;udevadm settle;sleep 2
resize2fs "$part";e2fsck -f -y "$part" || test $? -le 1
after=$(dumpe2fs -h "$part" 2>/dev/null | awk -F: '/^Block count/{print $2+0}');test "$after" -gt "$before"
m=/mnt/piu-grow;mkdir -p "$m";! mountpoint -q "$m";mount -o ro "$part" "$m";df -h "$m" | tail -1;ls "$m/game" | wc -l;umount "$m"
echo "DISCO_AMPLIADO bloques $before -> $after"
