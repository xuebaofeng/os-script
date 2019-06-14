sc stop "WSearch"
sc config "WSearch" start= disabled
rem sc config "WSearch" start= delayed-auto
rem sc start "WSearch"

rem disable bitlocker
manage-bde c: -protectors -disable

rem hyper v
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V –All
rem Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
