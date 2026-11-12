bash /mnt/d/PIU_INFINITY/mount_ro.sh >/dev/null 2>&1
cd /mnt/d/PIU_INFINITY/channels && python3 "$@" 2>&1 | tail -15
