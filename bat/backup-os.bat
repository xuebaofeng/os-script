cd c:\PortableApps\FreeFileSyncPortable\App\FreeFileSync\
FreeFileSync backup.ffs_batch

set location="c:\wbem"
cd %location%\github\os-script

copy "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\startup.bat" .\bat

git pull
git add -A
git commit -m 'backup'
git push