tee -a file.txt <<EOF
session=xfce
geometry=2560x1440
alwaysshared
EOF

systemctl enable vncserver@:1
systemctl start vncserver@:1
