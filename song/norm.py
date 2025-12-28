import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# 音乐目录
MUSIC_DIR = r"C:\BaiduNetdiskDownload"

# 支持的扩展名，只处理 opus 和 mp3
SUPPORTED_EXT = ['.opus', '.mp3']

# 最大线程数
MAX_WORKERS = 8  # 根据 CPU 核心数调节

def process_file(file_path):
    """
    转码单个文件，覆盖原文件
    """
    base, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()

    # 临时文件名
    tmp_file = f"{base}.tmp{ext_lower}"

    if ext_lower == '.opus':
        cmd = [
            'ffmpeg', '-y', '-i', file_path,
            '-vn', '-c:a', 'libopus', '-b:a', '128k',
            '-af', 'loudnorm',
            tmp_file
        ]
    elif ext_lower == '.mp3':
        cmd = [
            'ffmpeg', '-y', '-i', file_path,
            '-vn', '-c:a', 'libmp3lame', '-b:a', '192k',
            '-af', 'loudnorm',
            tmp_file
        ]
    else:
        # 不处理 m4a 或其他格式
        return f"Skipped: {file_path}"

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.replace(tmp_file, file_path)
        return f"Processed: {file_path}"
    except subprocess.CalledProcessError as e:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        return f"Failed: {file_path}, {e}"

def main():
    files = []
    for root, _, filenames in os.walk(MUSIC_DIR):
        for name in filenames:
            if os.path.splitext(name)[1].lower() in SUPPORTED_EXT:
                files.append(os.path.join(root, name))

    print(f"Found {len(files)} files to process...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_file, f) for f in files]
        for future in as_completed(futures):
            print(future.result())

if __name__ == "__main__":
    main()
