#install zsh, git

apt install zsh
chsh -s /bin/zsh

cd ~
mkdir github
cd github

#install oh-my-zsh
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"

#install fasd
git clone https://github.com/clvv/fasd
cd ~/github/fasd 
sudo make install


#install classifier
pip install classifier

#install sdkman, jenv
curl -s "https://get.sdkman.io" | bash

#copy config
cd ~/github
git clone https://github.com/xuebaofeng/os-script.git
rsync -aP ~/github/os-script/dot/ ~/
