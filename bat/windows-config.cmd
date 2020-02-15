sc stop "WSearch"
sc config "WSearch" start= disabled
rem sc config "WSearch" start= delayed-auto
rem sc start "WSearch"

rem disable bitlocker
rem manage-bde c: -protectors -disable

rem hyper v
rem Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V –All
rem Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All

wmic computersystem where name="%computername%" set AutomaticManagedPagefile=False
wmic pagefileset where name="C:\\pagefile.sys" set InitialSize=2048,MaximumSize=2048


# remove windows 10 apps

get-appxpackage *photos* | remove-appxpackage

get-appxpackage *zunevideo* | remove-appxpackage

DISM /online /disable-feature /featurename:WindowsMediaPlayer
Disable-WindowsOptionalFeature -Online -FeatureName "WindowsMediaPlayer"
