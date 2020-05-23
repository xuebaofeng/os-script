## install kind
cd /shared/k8s/
FILE=./kind
if [ -f "$FILE" ]; then
    echo "$FILE exist"
else
    echo "$FILE does not exist"
    curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.8.1/kind-$(uname)-amd64
    chmod +x ./kind
    sudo install kind /usr/local/bin
fi

## speed up the docker pull image
#docker save kindest/node > /shared/k8s/kindest_node.tar
docker load < /shared/k8s/kindest_node.tar

## create cluster
if kind get clusters | grep -q 'kind'; then
  echo "cluster kind exist"
else
  kind create cluster --config /shared/github.wdf/k8s-local-env/One-Click-Setup/DevVM/kind-config.yaml
fi

## increase /tmp size
#sudo mount -o remount,size=50G /tmp/

## load image
BIZX_IMGS="/shared/k8s/bizx-images.txt"
REGISTRY="saas-docker-dub.mo.sap.corp"
grep -vE '^(\s*$|#)' $BIZX_IMGS | {
while read IMG_PATH VER; do
  kind load docker-image ${REGISTRY}/${IMG_PATH}:${VER}
done
}

## copy ca
docker exec -it kind-control-plane /bin/sh -c "cp /usr/share/ca-certificates/sap/*.* /etc; update-ca-certificates 2>/dev/null"

## install kubectl
#yay -S kubectl

## install controller
helm upgrade -i kubernetes-bizxenvironment-controller /shared/github.wdf/bizx-controller/helm --set image.tag=0.8.9

## deploy cluster
export KCBX=/shared/github.wdf/k8s-local-env/BizX/exampleyamls
kubectl apply -f ${KCBX}/pv-tomcat.yaml
kubectl apply -f ${KCBX}/pvc-tomcat.yaml
kubectl delete MutatingWebhookConfiguration kubernetes-bizxenvironment-controller
kubectl delete ValidatingWebhookConfiguration kubernetes-bizxenvironment-controller
kubectl apply -f ${KCBX}/mybizx-newcode-HANA-local.yaml


# dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-beta8/aio/deploy/recommended.yaml
kubectl apply -f /shared/github.wdf/k8s-local-env/One-Click-Setup/DevVM/kube-dashboard-user.yaml
kubectl proxy &
kubectl -n kubernetes-dashboard describe secret $(kubectl -n kubernetes-dashboard get secret | grep admin-user | awk '{print $1}')

