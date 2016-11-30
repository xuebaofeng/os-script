cd %USERPROFILE%\github\os-script

copy "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\startup.bat" .\bat

git pull
git add -A
git commit -m 'backup'
git push