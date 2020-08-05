#!/usr/bin/env bash
# fix vmware tools file share function
FILE=/mnt/hgfs

if [ -f "$FILE" ]; then
    echo "$FILE exists."
else 
    echo "$FILE does not exist."
    sudo mkdir ${FILE}
fi

s=${FILE}/vm

if [ -f "$s" ]; then
    echo "$s exists."
else 
    echo "$s does not exist."
    cd /usr/bin
    sudo ./vmhgfs-fuse -o allow_other -o auto_unmount ${FILE}
fi

cd ${FILE}
ls .
