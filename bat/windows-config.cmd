sc stop "WSearch"
sc config "WSearch" start= disabled
rem sc config "WSearch" start= delayed-auto
rem sc start "WSearch"

rem disable bitlocker
rem manage-bde c: -protectors -disable

wmic computersystem where name="%computername%" set AutomaticManagedPagefile=False
wmic pagefileset where name="C:\\pagefile.sys" set InitialSize=2048,MaximumSize=2048

powercfg.exe /hibernate off

DISM /online /disable-feature /featurename:WindowsMediaPlayer
rem Disable-WindowsOptionalFeature -Online -FeatureName "WindowsMediaPlayer"
rem mklink /j "%UserProfile%\OneDrive\backup" C:\Users\I854966\Downloads\

@REM reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Mozilla /f
@REM reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Google /f

winget uninstall MicrosoftWindows.Client.WebExperience_cw5n1h2txyewy