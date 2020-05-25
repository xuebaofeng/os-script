kubectl delete -f /shared/k8s/pv-pod.yaml
kubectl delete -f /shared/k8s/pv-claim.yaml
kubectl delete -f /shared/k8s/pv-volume.yaml

kubectl apply -f /shared/k8s/pv-volume.yaml
kubectl apply -f /shared/k8s/pv-claim.yaml
kubectl apply -f /shared/k8s/pv-pod.yaml

echo "kubectl exec -it task-pv-pod -- ls /usr/share/nginx/html/"
