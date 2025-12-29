schtasks /create /sc minute /mo 1 /tn "KillFirefoxEveryMinute" /tr "taskkill /IM firefox.exe /F"
