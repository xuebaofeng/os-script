##/usr/local/bin/k3s-uninstall.sh

cd /shared/k8s/
export K3S_KUBECONFIG_MODE="644"

curl -sfL https://get.k3s.io | sh -

## setup
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

## load docker images
#sudo mkdir /var/lib/rancher/k3s/agent/images/
#for f in /shared/k8s/*.tar; do
#  echo "sudo rsync -av --progress sudo cp $f /var/lib/rancher/k3s/agent/images/"
#  sudo rsync -av --progress sudo cp $f /var/lib/rancher/k3s/agent/images/
#done

#sudo systemctl restart k3s
sudo k3s crictl images
echo "sudo k3s crictl images"
