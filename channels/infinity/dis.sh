cd /mnt/d/PIU_INFINITY/root_game
[ -s /mnt/d/PIU_INFINITY/dis.txt ] || objdump -d --no-show-raw-insn infinity_1_10_final_full > /mnt/d/PIU_INFINITY/dis.txt
wc -l /mnt/d/PIU_INFINITY/dis.txt
for a in 854c070 8542780 856003b 855f0b5 855f486 8563ec3 8546690 8545950 8545050 8544910 8547810; do echo "== callers of $a: $(grep -c "call   $a" /mnt/d/PIU_INFINITY/dis.txt)"; grep -B0 "call   $a" /mnt/d/PIU_INFINITY/dis.txt | head -5; done
