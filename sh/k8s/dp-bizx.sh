## deploy cluster
export KCBX=/shared/k8s
kubectl apply -f ${KCBX}/pv-tomcat.yaml
kubectl apply -f ${KCBX}/pvc-tomcat.yaml
kubectl delete MutatingWebhookConfiguration kubernetes-bizxenvironment-controller
kubectl delete ValidatingWebhookConfiguration kubernetes-bizxenvironment-controller
kubectl apply -f ${KCBX}/mybizx-newcode-HANA-local.yaml
