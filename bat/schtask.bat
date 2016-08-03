schtasks /Delete /TN "backup vm" /F
schtasks /create /sc WEEKLY /tn "backup vm" /tr "c:\green\bat\backup-vm.bat" /d wed /st 12:00
