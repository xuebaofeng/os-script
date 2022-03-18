
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted -Force

get-appxpackage *photos* | remove-appxpackage
get-appxpackage *zunevideo* | remove-appxpackage
get-appxpackage Microsoft.GamingServices | remove-AppxPackage -allusers

Set-MpPreference -DisableRealtimeMonitoring $true