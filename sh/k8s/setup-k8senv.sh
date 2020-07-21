# Add this into .bashrc
# source /shared/github/os-script/sh/k8s/setup-k8senv.sh
export PATH=/shared/github/os-script/sh/k8s/:$PATH

source <(kubectl completion bash)
alias k=kubectl
complete -F __start_kubectl k
