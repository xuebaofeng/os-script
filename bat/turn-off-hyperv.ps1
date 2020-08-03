Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
bcdedit /set hypervisorlaunchtype off
#bcdedit /set hypervisorlaunchtype auto
dism.exe /Online /Disable-Feature:Microsoft-Hyper-V-All