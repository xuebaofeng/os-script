cd %USERPROFILE%\github\backup
git pull

copy %USERPROFILE%\Downloads\my-umatrix-rules*.txt .\chrome\umatrix\

git add -A
git commit -m 'backup'
git push