kubectl version --client
kubectl cluster-info

sudo ll /var/lib/rancher/k3s/agent/images/
sudo k3s crictl images

sudo systemctl status k3s

watch kubectl get pods

kubectl -n local-path-storage get pod
kubectl -n local-path-storage logs -f local-path-provisioner-

kubectl get storageclass,pvc,pv


kubectl logs -f bx-cf-

## uninstall
/usr/local/bin/k3s-uninstall.sh

sudo rsync -av --progress /shared/k8s/bizx-database_hana-rmda.tar /var/lib/rancher/k3s/agent/images/
sudo rsync -av --progress sudo cp /shared/k8s/bizx_kafka.tar /var/lib/rancher/k3s/agent/images/
sudo rsync -av --progress sudo cp /shared/k8s/bizx_tomcat_empty.tar /var/lib/rancher/k3s/agent/images/
sudo rsync -av --progress sudo cp /shared/k8s/bizx_zookeeper.tar /var/lib/rancher/k3s/agent/images/

