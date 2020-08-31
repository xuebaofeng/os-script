rem copy "C:\SAPDevelop\github\os-script\bat\remove-browser-manage.bat" "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\"

reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Mozilla /f
reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Google /f

DisableCredGuard.bat