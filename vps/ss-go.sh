install_go() {

echo "install dependencies"

apt-get -y install software-properties-common
#python-software-properties

#add-apt-repository -y ppa:duh/golang
apt-get update
apt-get -y install golang

echo "golang installed, setup env..."
mkdir /usr/lib/gopath
env_persist_location=/etc/environment

echo "GOROOT=/usr/lib/go" >>  $env_persist_location
echo "GOBIN=/usr/bin/go" >>   $env_persist_location
echo "GOPATH=/usr/lib/gopath" >>   $env_persist_location
source  $env_persist_location

}



install_ss(){

apt-get -y install git curl

export GOPATH=/usr/lib/gopath

ssversion=1.1.4
lversion=linux64
wget -N http://dl.chenyufei.info/shadowsocks/$ssversion/shadowsocks-server-$lversion-$ssversion.gz
gunzip -c shadowsocks-server-$lversion-$ssversion.gz > /usr/bin/ssserver
chmod +x /usr/bin/ssserver


echo "Getting Public IP address, Please wait a moment..."
IP=`curl -s checkip.dyndns.com | cut -d' ' -f 6 | cut -d'<' -f 1`
cat >/etc/shadowsocks.json<<EOF 
{
    "server":"$IP",
    "server_port":8388,
    "password":"test",
    "timeout":300,
    "method":"aes-256-cfb"
}
EOF

service supervisor start
supervisorctl reload

}


install_supervisor(){
apt-get -y install supervisor
cat >/etc/supervisor/conf.d/shadowsocks.conf<<EOF 
[program:shadowsocks]
command=ssserver -c /etc/shadowsocks.json
autostart=true
autorestart=true
user=nobody
EOF
}


install_go
install_ss
install_supervisor
