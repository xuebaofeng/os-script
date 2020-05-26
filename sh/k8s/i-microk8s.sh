#snap install microk8s --classic --channel=1.18/stable
export PATH=/var/lib/snapd/snap/bin:$PATH
sudo usermod -a -G microk8s bx
sudo chown -f -R bx ~/.kube
newgrp microk8s
sudo microk8s enable dns dashboard registry helm

#microk8s ctr image import /shared/k8s/bizx_zookeeper.tar
for f in /shared/k8s/*.tar; do
 echo "microk8s ctr image import $f"
 microk8s ctr image import $f
done

microk8s.helm init
microk8s helm upgrade -i kubernetes-bizxenvironment-controller /shared/k8s/helm --set image.tag=0.8.9

export KCBX=/shared/k8s
microk8s kubectl apply -f ${KCBX}/pv-tomcat.yaml
microk8s kubectl apply -f ${KCBX}/pvc-tomcat.yaml
microk8s kubectl delete MutatingWebhookConfiguration kubernetes-bizxenvironment-controller
microk8s kubectl delete ValidatingWebhookConfiguration kubernetes-bizxenvironment-controller
microk8s kubectl apply -f ${KCBX}/mybizx-newcode-HANA-local.yaml
