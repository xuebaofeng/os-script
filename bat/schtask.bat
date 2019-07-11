set location="c:\SAPDevelop\github\os-script\bat"

schtasks /Delete /TN "backup os" /F
schtasks /create /sc WEEKLY /tn "backup os" /tr "%location%\backup-os.bat" /d MON,WED,THU  /st 11:30

schtasks /Delete /TN "backup to sap github" /F
schtasks /create /sc WEEKLY /tn "backup to sap github" /tr "%location%\backup-to-sap-github.bat" /d MON,TUE,WED /st 12:00

schtasks /Delete /TN "Code update" /F
schtasks /create /sc WEEKLY /tn "Code update" /tr "%location%\code-update.bat" /d MON,WED,THU  /st 12:30
