schtasks /Delete /TN "backup vm" /F
schtasks /create /sc WEEKLY /tn "backup vm" /tr "c:\green\bat\backup-vm.bat" /d wed /st 12:00

schtasks /Delete /TN "backup os" /F
schtasks /create /sc WEEKLY /tn "backup os" /tr "c:\green\bat\backup-os.bat" /d wed /st 12:00