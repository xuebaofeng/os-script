"C:\Program Files\FreeFileSync\FreeFileSync.exe" %USERPROFILE%\onedrive\conf\office-c-d.ffs_batch
"C:\Program Files\FreeFileSync\FreeFileSync.exe" %USERPROFILE%\onedrive\conf\office-c-f.ffs_batch
"C:\Program Files\FreeFileSync\FreeFileSync.exe" %USERPROFILE%\onedrive\conf\office-c-g.ffs_batch

set location="c:\wbem"
cd %location%\github\os-script

copy "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\startup.bat" .\bat

git pull
git add -A
git commit -m 'backup'
git push