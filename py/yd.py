import yt_dlp


save_path = 'c:/baidunetdiskdownload/'

# 配置
ydl_opts = {
    'format': 'bestaudio[ext=webm]',  # 优先 Opus 音轨
    'outtmpl': save_path +'/%(title)s.%(ext)s',  # 输出文件夹 + 文件名
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',  # 提取音频
        'preferredcodec': 'opus',      # 转成 Opus
        'preferredquality': '0',       # VBR 最高质量
    }],
    'quiet': False,  # 显示下载进度
    'noplaylist': False,  # 支持播放列表
}

# 视频 URL 列表，可直接放多个
video_urls = [
    'https://www.youtube.com/watch?v=C7wLiOdaAHk',
]

# 批量下载
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(video_urls)
