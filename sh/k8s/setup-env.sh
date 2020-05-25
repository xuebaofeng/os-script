export REGISTRY=saas-docker-dub.mo.sap.corp
export JAVA_HOME=/shared/sapjvm_8
export PATH=$JAVA_HOME/bin:$PATH
export GRADLE_USER_HOME=/shared/.gradle
export GRADLE_WORKSPACE=/shared/gradle_workspace
export PATH=/shared/github/os-script/sh/k8s/:/shared/github/os-script/sh/:$PATH
export GRADLE_USER_HOME=/shared/.gradle
export GRADLE_WORKSPACE=/shared/gradle_workspace

source <(kubectl completion bash)
alias k=kubectl
complete -F __start_kubectl k

alias ll='ls -alth'
alias sudo='sudo '
