choco install -y privoxy

python change_privoxy.py

cd "C:\Program Files (x86)\Privoxy"
privoxy.exe --install
net start privoxy
sc config privoxy start= auto

pip install psutil

