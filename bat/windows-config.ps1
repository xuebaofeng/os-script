# remove windows 10 apps
get-appxpackage *photos* | remove-appxpackage
get-appxpackage *zunevideo* | remove-appxpackage
DISM /online /disable-feature /featurename:WindowsMediaPlayer
Disable-WindowsOptionalFeature -Online -FeatureName "WindowsMediaPlayer"
