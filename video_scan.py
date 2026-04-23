import os
import subprocess

# 文件夹路径
folder = r"C:\shared\srfc2012"
folder = r"C:\BaiduNetdiskDownload"
# 支持的视频扩展名
video_exts = [".mp4", ".mkv", ".mov", ".avi"]

# 转码评分规则
def score_video(info, file_size):
    score = 0
    # 编码不是 H.264 / H.265
    if info.get("codec_name") not in ["hevc"]:
        score += 1
    # 视频码率过高 (>10Mbps)
    try:
        bit_rate = int(info.get("bit_rate", 0))
        if bit_rate > 10_000_000:
            score += 1
    except (ValueError, TypeError):
        # bit_rate 无效，忽略评分
        pass
    # 分辨率大于 1080p
    try:
        width = int(info.get("width", 0))
        if width > 1920:
            score += 1
    except (ValueError, TypeError):
        pass
    return score

# 获取视频信息
def get_video_info(path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,bit_rate",
        "-of", "default=noprint_wrappers=1:nokey=0", path
    ]
    output = subprocess.run(cmd, capture_output=True, text=True)
    info = {}
    for line in output.stdout.splitlines():
        if '=' in line:
            k, v = line.strip().split('=', 1)
            info[k] = v
    return info

# 扫描文件夹
videos_to_transcode = []

for root, dirs, files in os.walk(folder):
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in video_exts:
            # 跳过 _1080p.mp4 结尾的文件
            if f.endswith("_1080p.mp4"):
                continue
            path = os.path.join(root, f)
            file_size = os.path.getsize(path)
            info = get_video_info(path)
            score = score_video(info, file_size)
            if score >= 1:
                videos_to_transcode.append({
                    "path": path,
                    "score": score,
                    "codec": info.get("codec_name"),
                    "resolution": f"{info.get('width')}x{info.get('height')}",
                    "bitrate": info.get("bit_rate"),
                    "size_gb": round(file_size / (1024**3), 2)
                })

# 输出结果
if videos_to_transcode:
    print("===== 建议转码的视频 =====")
    for v in videos_to_transcode:
        print(f"{v['path']}\n  分数: {v['score']}, 编码: {v['codec']}, 分辨率: {v['resolution']}, "
              f"码率: {v['bitrate']}, 大小: {v['size_gb']} GB")
    print("\n===== 批量转码命令示例 (转 H.265 1080p) =====")
    for v in videos_to_transcode:
        output_file = os.path.splitext(v['path'])[0] + "_1080p.mp4"
        print(f'ffmpeg -i "{v["path"]}" -c:v libx265 -preset fast -crf 23 -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -maxsize 1920x1080 -c:a aac "{output_file}"')
else:
    print("没有找到明显需要转码的视频。")