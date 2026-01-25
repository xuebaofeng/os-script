schtasks /Delete /TN "backup DCIM" /F
schtasks /create /sc daily /tn "backup DCIM" /tr "C:\green\bin\backup-dcim.bat" /st 22:55

schtasks /delete /tn "DailyShutdown" /f
schtasks /create /tn "DailyShutdown" /tr "shutdown -s -f -t 0" /sc daily /st 22:25


schtasks /delete /tn "DiskCheckBark" /f