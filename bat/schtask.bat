set location="c:\wbem\github\os-script\bat"
schtasks /Delete /TN "backup vm" /F
schtasks /create /sc WEEKLY /tn "backup vm" /tr "%location%\backup-vm.bat" /d wed /st 12:00

schtasks /Delete /TN "backup os" /F
schtasks /create /sc WEEKLY /tn "backup os" /tr "%location%\backup-os.bat" /d MON,TUE,WED  /st 12:30

schtasks /Delete /TN "backup to sap github" /F
schtasks /create /sc WEEKLY /tn "backup to sap github" /tr "%location%\backup-to-sap-github.bat" /d MON,TUE,WED /st 12:30