schtasks /Delete /TN "backup DCIM" /F
schtasks /create /sc HOURLY /tn "backup DCIM" /tr "C:\green\bin\backup-dcim.bat"
