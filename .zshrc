

export GOPATH=/Users/bxue/gowork
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.8.0_60.jdk/Contents/Home
export GRADLE_HOME=/Applications/gradle-2.9
export M2_HOME=/Applications/apache-maven-3.3.9
export PATH=$GOPATH/bin:$GRADLE_HOME/bin:$JAVA_HOME/bin:$M2_HOME/bin:$PATH

eval "$(fasd --init auto)"

source $ZSH/oh-my-zsh.sh

