bash /mnt/d/PIU_INFINITY/mount_ro.sh >/dev/null 2>&1
cd /mnt/d/PIU_INFINITY && python3 tags.py 2>&1 | tail -120
