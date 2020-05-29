cd /shared/k8s/
export K3S_KUBECONFIG_MODE="644"

FILE=./k3s
if [ -f "$FILE" ]; then
    echo "$FILE exist"
else
    echo "$FILE does not exist"
    curl -Lo $FILE https://get.k3s.io
    chmod +x $FILE
    $FILE
fi

## setup
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

## load docker images
#sudo mkdir /var/lib/rancher/k3s/agent/images/
#for f in /shared/k8s/*.tar; do
#  echo "sudo rsync -av --progress sudo cp $f /var/lib/rancher/k3s/agent/images/"
#  sudo rsync -av --progress sudo cp $f /var/lib/rancher/k3s/agent/images/
#done

#sudo systemctl restart k3s

kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
