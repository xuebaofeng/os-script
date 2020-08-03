cd C:\media\download\
spotdl -p https://open.spotify.com/playlist/35zKStp8bpZhGYbUK3xUUw
for /r %%i in (*.txt) do spotdl -l %%i --overwrite skip
rem C:\SAPDevelop\github\podcast-dl\rename.bat