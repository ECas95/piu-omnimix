bash /mnt/d/PIU_INFINITY/mount_ro.sh >/dev/null 2>&1
ls /mnt/inf1/mnt
chroot /mnt/inf1 /bin/ls /root/game && echo CHROOT_OK
ls /mnt/inf1/usr/bin/ | grep -i -E "^gdb|strace|ltrace"
gcc -m32 -x c -o /tmp/t32 - <<'C'
int main(){return 0;}
C
echo m32=$?
