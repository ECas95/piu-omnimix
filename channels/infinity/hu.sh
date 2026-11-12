bash /mnt/d/PIU_INFINITY/mount_ro.sh >/dev/null 2>&1
for f in d_0002 p_0010 p_0011 d_0001; do echo == $f; stat -c %s /mnt/inf3/$f.dat; head -c 64 /mnt/inf3/$f.dat | xxd; done
