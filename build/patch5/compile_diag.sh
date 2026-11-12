#!/bin/bash
set -euo pipefail
root=/mnt/piu-diag-abi-root;cache=/mnt/c/Users/USER/.codex/workspaces/anime_channel_cache
image='/mnt/e/Pump It Up Data/PIU/PRIME RAW.img';mkdir -p "$root";! mountpoint -q "$root"
mount -o loop,ro,noload,offset=1048576,sizelimit=1998585856 "$image" "$root"
cleanup(){ code=$?;trap - EXIT;mountpoint -q "$root/mnt" && umount "$root/mnt";umount "$root";exit "$code"; }
trap cleanup EXIT
mount --bind "$cache" "$root/mnt"
b=/mnt/native_build/merged17_v363_runtime/trial;h="$cache/native_build/merged17_v363_runtime/trial"
ls "$h" | head -30
cp '/mnt/d/Pump It Up Data/PIU/final_v363/patch5/bga_diag.c' "$h/bga_diag.c"
src=$(cd "$h";ls *.c | grep -v '^test' | sed "s#^#$b/#" | tr '\n' ' ');echo $src
chroot "$root" env TMPDIR=/mnt/native_build/tmp gcc -m32 -shared -fPIC -O2 -msse2 -I"$b" $src -o "$b/m_bga_diag.so" -ldl -lpthread -lrt
cp "$h/m_bga_diag.so" '/mnt/d/Pump It Up Data/PIU/final_v363/patch5/m_bga_diag.so';rm -f "$h/bga_diag.c" "$h/m_bga_diag.so";echo BUILT
