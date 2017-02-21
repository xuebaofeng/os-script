export ZSH=$HOME/.oh-my-zsh

ZSH_THEME="maran"

plugins=(gradle svn)

eval "$(fasd --init auto)"

source /etc/bash.bashrc.local
source $ZSH/oh-my-zsh.sh

#setopt PROMPT_SUBST

export CATALINA_HOME=/data/sfsf/workspace/trunk/tomcat-sfs
export REGISTRY=saas-docker-dub.mo.sap.corp
export PATH=~/github/os-script/sh:$PATH
alias showproxy='env | grep -i proxy && cat ~/.curlrc'
alias gradle='gradle --profile'
# Set Proxy
function setproxy() {
  export {http,https,ftp}_proxy="http://10.14.126.17:8080"
  echo 'proxy = 10.14.126.17:8080' > ~/.curlrc
  echo 'Acquire::http::Proxy "http://10.14.126.17:8080";' > /etc/apt/apt.conf
  echo 'Acquire::https::Proxy "http://10.14.126.17:8080";' >> /etc/apt/apt.conf
  echo 'use_proxy=yes' > ~/.wgetrc
  echo 'http_proxy=10.14.126.17:8080' >> ~/.wgetrc
  showproxy
}

# Unset Proxy
function unsetproxy() {
  unset {http,https,ftp}_proxy
  rm ~/.curlrc
  rm ~/.wgetrc
  rm /etc/apt/apt.conf
  showproxy
}
