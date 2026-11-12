#!/bin/bash
mkdir -p /mnt/d/PIU_INFINITY/root_game
cp -a /mnt/inf1/root/game/. /mnt/d/PIU_INFINITY/root_game/ 2>&1 | head
cp /mnt/inf1/root/.xinitrc /mnt/d/PIU_INFINITY/root_game/_xinitrc
ls -la /mnt/d/PIU_INFINITY/root_game | head -50
cat /mnt/inf1/root/.xinitrc
file /mnt/inf1/root/game/infinity_1_10_final_full /mnt/inf1/root/game/doginf.so /mnt/inf1/root/game/pump
