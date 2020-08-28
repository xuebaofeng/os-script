#!/usr/bin/env bash

sudo mkdir /shared
mount /dev/sdb1 /shared

sudo mount-disk.sh

git config --global http.sslVerify false
git config --global credential.helper 'store --file=/shared/.git-credentials'
git config --global pull.rebase true
git config --global core.excludesFile '/shared/.gitignore'

pacman -S yay

yay -S --noconfirm snapd
sudo systemctl enable --now snapd.socket

yay -S --noconfirm fasd
yay -S --noconfirm docker
yay -S --noconfirm docker-compose
yay -S --noconfirm dbeaver
yay -S --noconfirm intellijidea-community
yay -S --noconfirm glances
yay -S --noconfirm ruby
yay -S --noconfirm graphviz
yay -S --noconfirm ncdu
yay -S --noconfirm npm

gem install soloist
#/home/bx/.gem/ruby/2.7.0/gems/soloist-1.0.3/bin/soloist
gem install librarian-chef

# fix vmware tools file share function
m-share.sh

curl -s "https://get.sdkman.io" | bash
sdk install gradle 6.4.1
sdk install ant 1.10.1
sdk install maven
MVN_HOME


openssl s_client -showcerts -connect saas-docker-dub.mo.sap.corp:443 < /dev/null | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /shared/sap.crt
sudo cp /shared/sap.crt /etc/ssl/certs/
sudo trust extract-compat
sudo mkdir -p /etc/docker/certs.d/saas-docker-dub.mo.sap.corp:443
sudo cp /shared/sap.crt /etc/docker/certs.d/saas-docker-dub.mo.sap.corp:443/
sudo usermod -aG docker $USER
sudo systemctl restart docker
#newgrp docker

docker load < /shared/k8s/bizx_tomcat_empty.tar
docker load < /shared/k8s/bizx_kafka.tar
docker load < /shared/k8s/bizx_zookeeper.tar
docker load < /shared/k8s/bizx-database_hana-rmda.tar

