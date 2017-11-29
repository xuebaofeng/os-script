mkdir r:\chrome-cache
mkdir r:\firefox-cache
mkdir r:\tmp
mkdir r:\temp
mkdir r:\u-tmp
mkdir r:\u-temp
mkdir r:\idm-temp
rd /s /q "C:\Users\I854966\AppData\Local\Google\Chrome\User Data\Default\Cache"
mklink /J "C:\Users\I854966\AppData\Local\Google\Chrome\User Data\Default\Cache" "r:\chrome-cache"
