schtasks /Delete /TN "backup vm" /F
schtasks /create /sc WEEKLY /tn "backup vm" /tr "%USERPROFILE%\github\os-script\bat\backup-vm.bat" /d thu /st 12:00

schtasks /Delete /TN "backup os" /F
schtasks /create /sc daily /tn "backup os" /tr "%USERPROFILE%\github\os-script\bat\backup-os.bat" /st 12:30

schtasks /Delete /TN "backup to sap github" /F
schtasks /create /sc daily /tn "backup to sap github" /tr "%USERPROFILE%\github\os-script\bat\backup-to-sap-github.bat" /st 12:30