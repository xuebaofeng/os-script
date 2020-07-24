#!/bin/bash
if ! grep -q 'init-poky' /etc/fstab ; then
    echo '# init-poky' >> /etc/fstab
    echo '/dev/sdb1 /shared 	 ext4	 defaults' >> /etc/fstab
fi