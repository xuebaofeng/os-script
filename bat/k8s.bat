rem choco uninstall -y docker-cli
rem choco uninstall -y docker-desktop
rem choco uninstall -y minikube
rem choco uninstall -y kubernetes-cli
rem choco uninstall -y kubernetes-helm

rem choco install -y docker-cli
rem choco install -y docker-desktop
rem choco install -y kubernetes-cli
rem choco install -y minikube
rem choco install -y kubernetes-helm

rem cp C:\SAPDevelop\github.wdf.sap.corp\k8s-local-env\One-Click-Setup\bizx-on-k8s-for-windows\ca-certificates\* ~\.minikube\files\etc\ssl\certs

rem for %%f in (C:\Users\I854966\Downloads\k8s\*.tar) do ( docker load -i %%f )

minikube cache add saas-docker-dub.mo.sap.corp/bizx-agents/zookeeper-exporter:latest
minikube cache add saas-docker-dub.mo.sap.corp/bizx-database/hana-rmda:trunk.weekly
minikube cache add saas-docker-dub.mo.sap.corp/bizx/kafka:2.11-1.1.0
minikube cache add saas-docker-dub.mo.sap.corp/bizx/tomcat_empty:trunk.version
minikube cache add saas-docker-dub.mo.sap.corp/bizx/zookeeper:3.4.14
minikube cache add saas-docker-dub.mo.sap.corp/kubernetes/bizxenvironment-controller:0.8.9

REM minikube delete
REM minikube start --driver=docker  --memory=22528 --cpus=10

helm upgrade -i kubernetes-bizxenvironment-controller C:\Users\I854966\Downloads\k8s\helm\ --set image.tag=0.8.9

kubectl apply -f C:\Users\I854966\Downloads\k8s\pv-tomcat.yaml
kubectl apply -f C:\Users\I854966\Downloads\k8s\pvc-tomcat.yaml
kubectl delete MutatingWebhookConfiguration kubernetes-bizxenvironment-controller
kubectl delete ValidatingWebhookConfiguration kubernetes-bizxenvironment-controller
kubectl apply -f C:\Users\I854966\Downloads\k8s\mybizx-newcode-HANA-local.yaml

REM minikube delete