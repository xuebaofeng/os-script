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
apt-get install -y curl git rsync python-pip terminator vim clipit fasd dos2unix
apt install -y docker.io htop glances
pip install docker-compose

ufw disable

chown -R i854966 /data

curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
rm /data/scripts/docker-compose