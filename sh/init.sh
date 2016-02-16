dnf install zsh vim -y
git clone https://github.com/xuebaofeng/os-script.git
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
chsh -s /bin/zsh
git clone https://github.com/clvv/fasd
cd fasd 
sudo make install
pip install classifier
