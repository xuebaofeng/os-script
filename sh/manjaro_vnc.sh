echo "
session=xfce
geometry=2560x1440
alwaysshared
" > ~/.vnc/config


echo ":1=bx" > /etc/tigervnc/vncserver.users

printf "111111\n111111\n\n" | vncpasswd

systemctl enable vncserver@:1
systemctl start vncserver@:1
