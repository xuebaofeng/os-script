#!/usr/bin/env bash
if [ $(id -u) -ne 0 ]; then
  echo "This script must be run as root";
  exit 1;
fi


#install packages
add-apt-repository -y ppa:gnome-terminator
add-apt-repository -y ppa:aacebedo/fasd
apt-get update
apt-get remove -y vim-common
apt-get install -y curl git rsync python-pip terminator vim clipit fasd
apt install -y docker.io htop glances
pip install docker-compose

ufw disable