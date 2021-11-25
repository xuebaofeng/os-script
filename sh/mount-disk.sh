#!/bin/bash
if ! grep -q 'init-poky' /etc/fstab ; then
    echo '# init-poky' >> /etc/fstab
    echo '/dev/sda3 /shared 	 ext4	 defaults' >> /etc/fstab
fi
cat /etc/fstab