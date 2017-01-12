#install zsh, git

add-apt-repository ppa:gnome-terminator
apt-get update

apt-get install -y zsh curl git rsync python-pip terminator
chsh -s $(which zsh) $(whoami)

cd ~
mkdir github
cd github

#install oh-my-zsh
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"

#install fasd
git clone https://github.com/clvv/fasd
cd ~/github/fasd 
make install


#install classifier
pip install classifier

#install sdkman, jenv
curl -s "https://get.sdkman.io" | bash

#copy config
cd ~/github
git clone https://github.com/xuebaofeng/os-script.git
rsync -aP ~/github/os-script/dot/ ~/
