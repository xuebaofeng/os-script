# Add this into .bashrc
# source /shared/github/os-script/sh/k8s/setup-env.sh
export REGISTRY=saas-docker-dub.mo.sap.corp
export PATH=/shared/github/os-script/sh/k8s/:/shared/github/os-script/sh/:$PATH
export GRADLE_USER_HOME=/shared/.gradle
export GRADLE_WORKSPACE=/shared/gradle_workspace
export ANT_HOME=/home/bx/.sdkman/candidates/ant/1.10.1

source <(kubectl completion bash)
alias k=kubectl
complete -F __start_kubectl k

alias ll='ls -alth'
alias sudo='sudo '
