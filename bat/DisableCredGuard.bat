@echo off


echo.
echo Delete registry settings:
REM reg delete HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\LSA /v LsaCfgFlags /f
REM reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DeviceGuard /v LsaCfgFlags /f
reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DeviceGuard /v EnableVirtualizationBasedSecurity /f
reg delete HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DeviceGuard /v RequirePlatformSecurityFeatures /f


echo.
echo Delete the Windows Defender Credential Guard EFI variables by using bcdedit:
mountvol X: /s
copy %WINDIR%\System32\SecConfig.efi X:\EFI\Microsoft\Boot\SecConfig.efi /Y
bcdedit /create {0cb3b571-2f2e-4343-a879-d86a476d7215} /d "DebugTool" /application osloader
bcdedit /set {0cb3b571-2f2e-4343-a879-d86a476d7215} path "\EFI\Microsoft\Boot\SecConfig.efi"
bcdedit /set {bootmgr} bootsequence {0cb3b571-2f2e-4343-a879-d86a476d7215}

REM Disable Credential Guard & virtualization-based security
REM bcdedit /set {0cb3b571-2f2e-4343-a879-d86a476d7215} loadoptions DISABLE-LSA-ISO,DISABLE-VBS
bcdedit /set {0cb3b571-2f2e-4343-a879-d86a476d7215} loadoptions DISABLE-VBS

bcdedit /set vsmlaunchtype off

bcdedit /set {0cb3b571-2f2e-4343-a879-d86a476d7215} device partition=X:
mountvol X: /d


echo.
echo Disable Hyper-V if the feature is installed on Windows:
bcdedit /set hypervisorlaunchtype off

remove-browser-manage.bat
