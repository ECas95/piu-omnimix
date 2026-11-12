#!/bin/bash
# Inside the throw-away layer only: swap the cabinet module for the matching keyboard (trial) module.
set -euo pipefail
work='/mnt/d/Pump It Up Data/PIU/final_v363/cabinet';root=/mnt/piu-cabinet-root
modprobe nbd max_part=8;device=''
for c in /sys/block/nbd*;do if test ! -e "$c/pid";then device="/dev/${c##*/}";break;fi;done
mkdir -p "$root";! mountpoint -q "$root"
endpoint=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["endpoint"])' "$work/native_nbd_server.json")
qemu-nbd --cache=writeback --format=raw --connect="$device" --fork "$endpoint"
cleanup(){ code=$?;trap - EXIT;mountpoint -q "$root" && umount "$root";qemu-nbd --disconnect "$device" || code=1;exit "$code"; }
trap cleanup EXIT
for a in $(seq 1 30);do test -b "${device}p1" && break;sleep .2;done
mount "${device}p1" "$root";m="$root/root/game/m.so";now=$(sha256sum "$m" | cut -d' ' -f1)
trial=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$work/teclado_map.json" "$now")
test -n "$trial" || { echo "m.so del disco desconocido ($now)";exit 1; }
cp "$trial" "$m.new";chmod 755 "$m.new";mv -f "$m.new" "$m";sync -f "$root"
echo "modulo de prueba con teclado instalado en la capa: $(sha256sum "$m" | cut -d' ' -f1)"
