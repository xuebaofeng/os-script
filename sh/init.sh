#install zsh, git

chsh -s /bin/zsh

#install oh-my-zsh
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"


#install fasd
git clone https://github.com/clvv/fasd
cd fasd 
sudo make install


#install classifier
pip install classifier

#install sdkman
curl -s "https://get.sdkman.io" | bash


#copy config
git clone https://github.com/xuebaofeng/os-script.git
cp ~/github/os-script/dot/* .