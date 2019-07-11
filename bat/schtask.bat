set location="c:\SAPDevelop\github\os-script\bat"

schtasks /Delete /TN "backup os" /F
schtasks /create /sc WEEKLY /tn "backup os" /tr "%location%\backup-os.bat" /d MON,WED,THU  /st 11:30
