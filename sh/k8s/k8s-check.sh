kubectl version --client
#itVersion:"v1.18.2"

kubectl cluster-info

kind version
#kind v0.8.1 go1.14.2 linux/amd64

docker ps -a | grep kind
#141f67883363        kindest/node:v1.18.2

docker exec -it kind-control-plane crictl images

watch kubectl get pods

docker version
#Version:           19.03.8-ce
