mkdir a:\chrome-cache
mkdir a:\firefox-cache
mkdir a:\tmp
mkdir a:\temp
mkdir a:\u-tmp
mkdir a:\u-temp
mkdir a:\idm-temp
rd /s /q "C:\Users\I854966\AppData\Local\Google\Chrome\User Data\Default\Cache"
mklink /J "C:\Users\I854966\AppData\Local\Google\Chrome\User Data\Default\Cache" "a:\chrome-cache"
