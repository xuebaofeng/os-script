export KCBX=/shared/github.wdf/k8s-local-env/BizX/exampleyamls
kubectl apply -f ${KCBX}/mybizx-newcode-HANA-local.yaml
kubectl delete deployment bx-cf