schtasks /Delete /TN "backup DCIM" /F
schtasks /create /sc daily /tn "backup DCIM" /tr "C:\green\bin\backup-dcim.bat" /st 22:55
