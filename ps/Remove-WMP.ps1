Get-AppxPackage -AllUsers *Microsoft.ZuneMusic* | Remove-AppxPackage -AllUsers
Get-AppxPackage -AllUsers *Microsoft.MediaPlayer* | Remove-AppxPackage -AllUsers
Disable-WindowsOptionalFeature -Online -FeatureName WindowsMediaPlayer -NoRestart