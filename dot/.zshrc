export ZSH=$HOME/.oh-my-zsh

ZSH_THEME="maran"

plugins=(gradle svn)

eval "$(fasd --init auto)"

source /etc/bash.bashrc.local
source $ZSH/oh-my-zsh.sh

setopt PROMPT_SUBST

#export SMART_SWITCHER_DIR=~/github/smart_switcher-master; source $SMART_SWITCHER_DIR/smart_switcher.sh

export CATALINA_HOME=/data/sfsf/workspace/trunk/tomcat-sfs

alias g='gradle'
alias t='tail -f $CATALINA_HOME/logs/catalina.out'
