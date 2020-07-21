# Add this into .bashrc
# source /shared/github/os-script/sh/k8s/setup-env.sh
export REGISTRY=saas-docker-dub.mo.sap.corp
export JAVA_HOME=/shared/sapjvm_8
export PATH=$JAVA_HOME/bin:$PATH
export GRADLE_USER_HOME=/shared/.gradle
export GRADLE_WORKSPACE=/shared/gradle_workspace
export PATH=/shared/github/os-script/sh/k8s/:/shared/github/os-script/sh/:$PATH
export GRADLE_USER_HOME=/shared/.gradle
export GRADLE_WORKSPACE=/shared/gradle_workspace
export ANT_HOME=/home/bx/.sdkman/candidates/ant/1.10.1

alias ll='ls -alth'
alias sudo='sudo '
