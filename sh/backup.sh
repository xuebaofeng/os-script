#!/usr/bin/env bash
#sudo cp ~/github/os-script/sh/backup.sh /etc/cron.daily/

backup_dir="/mnt/hgfs/vm"

dirs=(dot sh)
if [ ! -d "${backup_dir}/dot" ]; then
  mkdir ${backup_dir}/dot
fi

files=(zshrc zsh_history gitconfig vimrc)
for item in ${files[*]}
do
    cp  ~/.$item ${backup_dir}/dot/
done