sc stop "WSearch"
sc config "WSearch" start= disabled

wmic computersystem where name="%computername%" set AutomaticManagedPagefile=False
wmic pagefileset where name="C:\\pagefile.sys" set InitialSize=2048,MaximumSize=2048

powercfg.exe /hibernate off

DISM /online /disable-feature /featurename:WindowsMediaPlayer /NoRestart

winget uninstall MicrosoftWindows.Client.WebExperience_cw5n1h2txyewy

