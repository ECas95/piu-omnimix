#!/bin/bash
cat /mnt/inf1/etc/fstab
echo "== services/autostart"; ls /mnt/inf1/etc/systemd/system/ /mnt/inf1/etc/init.d 2>/dev/null | head -40
grep -rl "piu\|infinity\|/mnt/hd" /mnt/inf1/etc/systemd /mnt/inf1/etc/init.d /mnt/inf1/etc/rc*.d /mnt/inf1/root /mnt/inf1/home 2>/dev/null | head
echo "== big executables"
find /mnt/inf1 -xdev -type f -size +2M -perm -u+x 2>/dev/null | grep -v -e /usr/lib/x86_64-linux-gnu -e /lib/modules -e firmware -e /boot -e /usr/bin -e /usr/sbin -e /usr/libexec | head -30
echo "== log"; head -40 /mnt/inf2/log.txt
