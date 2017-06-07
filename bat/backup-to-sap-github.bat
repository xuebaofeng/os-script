set location="c:\wbem"
cd %location%\github\backup
git pull

copy %USERPROFILE%\Downloads\my-umatrix-rules*.txt .\chrome\umatrix\
copy C:\data\sfsf\svn\trunk\*.bat .\bat\

git add -A
git commit -m 'backup'
git push