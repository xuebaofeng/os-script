set list="https://www.youtube.com/watch?v=iFSsJCr-VTc&list=PL9bhMn23X5WUeFHSImR2qdFEtPSrWjZpL"
cd C:\green\bin
yt-dlp -P "C:/baidunetdiskdownload" -f ba -o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" %list%