#!/usr/bin/env bash
if [ $(id -u) -ne 0 ]; then
  echo "This script must be run as root";
  exit 1;
fi

unset http_proxy
unset https_proxy

gsettings set org.gnome.desktop.screensaver lock-enabled false

#install packages
add-apt-repository -y ppa:gnome-terminator
apt-get update
apt-get remove -y vim-common
apt-get install -y curl git rsync python-pip terminator vim clipit
apt install -y docker.io htop glances
pip install docker-compose
chsh -s $(which bash) $(whoami)
usermod -s $(which bash) $(whoami)

#clone git
cd
mkdir github
cd github


#install fasd
cd ~
mkdir github
cd github
git clone https://github.com/clvv/fasd
cd fasd
make install


#install sdkman, jenv
curl -s "https://get.sdkman.io" | bash
chown -R $(whoami) ~/.sdkman

#copy config
cd ~/github
git clone https://github.com/xuebaofeng/os-script.git
rsync -aP ~/github/os-script/dot/ ~/

cd
chown -R $(whoami) .

cp ~/github/os-script/sh/backup /etc/cron.hourly/

