choco install -y privoxy

python change_privoxy.py

cd "C:\Program Files (x86)\Privoxy"
privoxy.exe --install
net start privoxy
sc config privoxy start= auto

pip install psutil

icacls C:\scripts /inheritance:r

icacls C:\scripts /grant %USERNAME%:(OI)(CI)F
icacls C:\scripts /grant SYSTEM:(OI)(CI)F
icacls C:\scripts /grant "NT AUTHORITY\LOCAL SERVICE":(OI)(CI)F
icacls C:\scripts /grant "NT AUTHORITY\NETWORK SERVICE":(OI)(CI)F

icacls C:\scripts /remove Users
icacls C:\scripts /remove Everyone