kubectl version --client
kubectl cluster-info

sudo ll /var/lib/rancher/k3s/agent/images/
watch sudo k3s crictl images

watch kubectl get pods

kubectl -n local-path-storage get pod
kubectl -n local-path-storage logs -f local-path-provisioner-

kubectl get storageclass,pvc,pv
