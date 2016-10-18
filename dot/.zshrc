export ZSH=$HOME/.oh-my-zsh

ZSH_THEME="maran"

plugins=(gradle svn)

eval "$(fasd --init auto)"

source /etc/bash.bashrc.local
source $ZSH/oh-my-zsh.sh

setopt PROMPT_SUBST

export SMART_SWITCHER_DIR=~/github/smart_switcher-master; source $SMART_SWITCHER_DIR/smart_switcher.sh

export CATALINA_HOME=/data/sfsf/workspace/trunk/tomcat-sfs

alias g='gradle'
alias t='tail -f $CATALINA_HOME/logs/catalina.out'
alias e-zsh='vim ~/.zshrc'
alias s-proxy='env | grep -i proxy'

# Set Proxy
function setproxy() {
  export {http,https,ftp}_proxy="http://proxy:8080"
}

# Unset Proxy
function unsetproxy() {
  unset {http,https,ftp}_proxy
}
