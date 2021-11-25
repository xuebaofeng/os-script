#!/usr/bin/env bash

sudo mkdir /shared
sudo mount /dev/sdb1 /shared

sudo mount-disk.sh

sudo pacman -S yay --noconfirm

yay -S --noconfirm fasd
yay -S --noconfirm glances
yay -S --noconfirm ncdu
yay -S --noconfirm jellyfin


yay -S --noconfirm docker
sudo systemctl start docker.service
sudo systemctl enable docker.service
sudo docker version