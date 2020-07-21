#!/usr/bin/env bash

sudo mkdir /shared
mount /dev/sdb1 /shared

pacman -S yay

yay -S --noconfirm snapd
sudo systemctl enable --now snapd.socket

yay -S --noconfirm fasd
yay -S --noconfirm docker
yay -S --noconfirm docker-compose
yay -S --noconfirm dbeaver
yay -S --noconfirm intellijidea-community

curl -s "https://get.sdkman.io" | bash
sdk install gradle 6.4.1

openssl s_client -showcerts -connect saas-docker-dub.mo.sap.corp:443 < /dev/null | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /shared/sap.crt
sudo cp /shared/sap.crt /etc/ssl/certs/
sudo trust extract-compat
sudo mkdir -p /etc/docker/certs.d/saas-docker-dub.mo.sap.corp:443
sudo cp /shared/sap.crt /etc/docker/certs.d/saas-docker-dub.mo.sap.corp:443/
sudo systemctl restart docker
sudo usermod -aG docker $USER
newgrp docker

docker load < /shared/k8s/bizx_tomcat_empty.tar
docker load < /shared/k8s/bizx_kafka.tar
docker load < /shared/k8s/bizx_zookeeper.tar
docker load < /shared/k8s/bizx-database_hana-rmda.tar

