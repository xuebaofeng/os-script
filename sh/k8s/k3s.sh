export K3S_KUBECONFIG_MODE="644"
#export INSTALL_K3S_EXEC=" --no-deploy servicelb --no-deploy traefik"
curl -sfL https://get.k3s.io | sh -
#sudo systemctl status k3s

## setup
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

## load docker images
sudo mkdir /var/lib/rancher/k3s/agent/images/
sudo cp /shared/k8s/*.tar /var/lib/rancher/k3s/agent/images/
sudo systemctl restart k3s

## list docker images
sudo k3s crictl images

kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml

## uninstall
#/usr/local/bin/k3s-uninstall.sh

