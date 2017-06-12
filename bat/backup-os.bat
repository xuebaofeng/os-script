c:\PortableApps\FreeFileSyncPortable\App\FreeFileSync\FreeFileSync c:\Users\I854966\Dropbox\conf\backup.ffs_batch

set location="c:\wbem"
cd %location%\github\os-script

copy "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp\startup.bat" .\bat

git pull
git add -A
git commit -m 'backup'
git push