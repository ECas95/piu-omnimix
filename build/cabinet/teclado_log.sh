#!/bin/bash
set -euo pipefail
work='/mnt/d/Pump It Up Data/PIU/final_v363/cabinet';m=/mnt/piu-cabinet-root
modprobe nbd max_part=8;device=''
for c in /sys/block/nbd*;do if test ! -e "$c/pid";then device="/dev/${c##*/}";break;fi;done
mkdir -p "$m";! mountpoint -q "$m"
endpoint=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["endpoint"])' "$work/native_nbd_server.json")
qemu-nbd --cache=writeback --format=raw --connect="$device" --fork "$endpoint"
cleanup(){ code=$?;trap - EXIT;mountpoint -q "$m" && umount "$m";qemu-nbd --disconnect "$device" || code=1;exit "$code"; }
trap cleanup EXIT
for a in $(seq 1 30);do test -b "${device}p2" && break;sleep .2;done
mount "${device}p2" "$m";cp "$m/PIU/bga.log" "$work/logs/bga.log";wc -l "$work/logs/bga.log";echo BGA_LOG_COPIADO
