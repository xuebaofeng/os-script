sc stop "WSearch"
sc config "WSearch" start= disabled

wmic computersystem where name="%computername%" set AutomaticManagedPagefile=False
wmic pagefileset where name="C:\\pagefile.sys" set InitialSize=2048,MaximumSize=2048

powercfg.exe /hibernate off

takeown /F "C:\$Windows.~BT\*" /A /R /D Y
icacls "C:\$Windows.~BT\*.*" /grant *S-1-5-32-544:F /T /C /Q
RD /S /Q "C:\$Windows.~BT"

tzutil /s "Pacific Standard Time"

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v TaskbarDa /t REG_DWORD /d 0 /f
taskkill /f /im explorer.exe & start explorer.exe
