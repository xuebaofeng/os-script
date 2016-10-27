export ZSH=$HOME/.oh-my-zsh

ZSH_THEME="maran"

plugins=(gradle svn)

eval "$(fasd --init auto)"

source /etc/bash.bashrc.local
source $ZSH/oh-my-zsh.sh

setopt PROMPT_SUBST

export CATALINA_HOME=/data/sfsf/workspace/trunk/tomcat-sfs
export GIT_CURL_VERBOSE=1

alias g='gradle'
alias t='tail -f $CATALINA_HOME/logs/catalina.out'
alias e-zsh='vim ~/.zshrc'
alias showproxy='env | grep -i proxy && cat ~/.curlrc'

# Set Proxy
function setproxy() {
  export {http,https,ftp}_proxy="http://proxy:8080"
  git config --global http.proxy http://proxy:8080
  git config --global https.proxy http://proxy:8080
  echo 'proxy = proxy:8080' > ~/.curlrc
  showproxy
}

# Unset Proxy
function unsetproxy() {
  unset {http,https,ftp}_proxy
  git config --global --unset http.proxy
  git config --global --unset https.proxy
  rm ~/.curlrc
  showproxy
}