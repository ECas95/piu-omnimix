#!/bin/bash
# Swaps /root/game/m.so on the cabinet disk (attached with wsl --mount --bare): diag <-> patch-1 cabinet module, or the patch-2 fix (fix).
set -euo pipefail
mode=$1;work='/mnt/d/Pump It Up Data/PIU/final_v363';r=/mnt/piu-swap-root
P1=/dev/disk/by-uuid/bde1a5e4-cc8e-448e-99f5-13cb09f70d72
cab="$work/patch/m_cabinet.so";diag="$work/diag/m_diag.so";trial="$work/patch/m_trial.so";diag2="$work/diag/m_diag2.so";fix="$work/patch2/m_cabinet.so"
cab_sha=$(sha256sum "$cab" | cut -d' ' -f1);diag_sha=$(sha256sum "$diag" | cut -d' ' -f1);trial_sha=$(sha256sum "$trial" | cut -d' ' -f1);diag2_sha=$(sha256sum "$diag2" | cut -d' ' -f1);fix_sha=$(sha256sum "$fix" | cut -d' ' -f1)
# earlier diagnostic / patch-2 builds that may still be on the disk
old=" 05ec15e03fe49c221eeed94265c12b46798f718b4f3141c3e25b7d688e135a1e 4a10c6c1f09525f8009e9d15fc9d645ba4724f9ae665608fb417a02c4e552236 01f679a0476be3d1f6948ab12884bd5d837132ce47a6354d862aa3921ba3ee79 "
udevadm settle;test -b "$P1" || { echo 'No es el disco del cabinet';exit 1; }
mkdir -p "$r";! mountpoint -q "$r"
cleanup(){ code=$?;trap - EXIT;mountpoint -q "$r" && umount "$r";exit "$code"; }
trap cleanup EXIT
mount "$P1" "$r";m="$r/root/game/m.so";now=$(sha256sum "$m" | cut -d' ' -f1)
case "$mode" in diag2) want="$diag2";want_sha="$diag2_sha";;diag) want="$diag";want_sha="$diag_sha";;mk5) want="$trial";want_sha="$trial_sha";;restore) want="$cab";want_sha="$cab_sha";;fix) want="$fix";want_sha="$fix_sha";;*) exit 2;;esac
case "$old" in *" $now "*) now_ok=1;; *) now_ok=0;; esac
test $now_ok = 1 -o "$now" = "$fix_sha" -o "$now" = "$cab_sha" -o "$now" = "$diag_sha" -o "$now" = "$trial_sha" -o "$now" = "$diag2_sha" || { echo "m.so desconocido ($now): no toco nada";exit 1; }
grep -q " /dev/ttyS0" "$r/root/.xinitrc" && sed -i "s# /dev/ttyS0##" "$r/root/.xinitrc" && echo "xinitrc: sin copia del log al puerto serie (como el disco de fabrica)"
if [ "$now" != "$want_sha" ];then cp "$want" "$m.swap-new";chmod 755 "$m.swap-new";mv -f "$m.swap-new" "$m";fi
sync -f "$r";umount "$r";e2fsck -p "$P1" || test $? -le 1
mount -o ro "$P1" "$r";test "$(sha256sum "$m" | cut -d' ' -f1)" = "$want_sha";echo "MODULO_${mode^^}_OK $want_sha"
