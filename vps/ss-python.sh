#!/bin/bash
echo "*begin to install vps"
echo "**install shadowsocks with supervisor"

echo $OSTYPE

apt-get update
apt-get -y install python-pip python-m2crypto supervisor curl nethogs
pip install shadowsocks

echo "Getting Public IP address, Please wait a moment..."
IP=`curl -s checkip.dyndns.com | cut -d' ' -f 6  | cut -d'<' -f 1`

cat >/etc/shadowsocks.json<<EOF 
{
    "server":"$IP",

    "server_port":8388,
    "password":"test",
    "timeout":300,
    "method":"aes-256-cfb"
}
EOF


cat >/etc/supervisor/conf.d/shadowsocks.conf<<EOF 
[program:shadowsocks]
command=ssserver -c /etc/shadowsocks.json
autostart=true
autorestart=true
user=nobody
EOF

service supervisor start
supervisorctl reload

#supervisorctl tail -f shadowsocks stderr
#supervisorctl restart shadowsocks
#apt-get install -y ntop deluge-web btsync

echo "**end install shadowsocks with supervisor"

echo "** begin install "
apt-get install shellinabox
useradd baofeng
echo "** end install shellinabox"

echo "*end install vps"
