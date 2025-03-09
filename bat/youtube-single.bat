set video="https://www.youtube.com/watch?v=kTJczUoc26U"
cd C:\green\bin
set ffmpeg="Z:\green\yt-dlp-gui\ffmpeg.exe"
yt-dlp --ffmpeg-location %ffmpeg% -f ba -P "C:/baidunetdiskdownload" %video%