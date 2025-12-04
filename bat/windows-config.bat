sc stop "WSearch"
sc config "WSearch" start= disabled

wmic computersystem where name="%computername%" set AutomaticManagedPagefile=False
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" `
    -Name "PagingFiles" `
    -Value "C:\pagefile.sys 2048 2048"

Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" `
    -Name "AutoManagedPagefile" `
    -Value 0

powercfg.exe /hibernate off

@REM takeown /F "C:\$Windows.~BT\*" /A /R /D Y
@REM icacls "C:\$Windows.~BT\*.*" /grant *S-1-5-32-544:F /T /C /Q
@REM RD /S /Q "C:\$Windows.~BT"
@REM tzutil /s "Pacific Standard Time"
@REM reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v TaskbarDa /t REG_DWORD /d 0 /f
@REM taskkill /f /im explorer.exe & start explorer.exe
