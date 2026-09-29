import os
import re
import sys
import time
import feedparser
import requests

RSS_URL = "https://rss.wbur.org/circleround/podcast"
OUTPUT_DIR = "Circle Round"

# None = 全部
# 例如 20 = 只下载最新20集
MAX_EPISODES = None

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("读取 RSS...")
feed = feedparser.parse(RSS_URL)

if not feed.entries:
    print("没有读取到节目，请检查网络或 RSS 地址。")
    sys.exit(1)

entries = feed.entries
if MAX_EPISODES:
    entries = entries[:MAX_EPISODES]

print(f"发现 {len(entries)} 集")

def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:180]

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 CircleRoundDownloader/1.0"
})

for i, entry in enumerate(entries, 1):

    title = entry.get("title", f"Episode {i}")

    # RSS enclosure 中通常就是 MP3 地址
    audio_url = None

    if entry.get("enclosures"):
        for enc in entry.enclosures:
            url = enc.get("href") or enc.get("url")
            if url:
                audio_url = url
                break

    if not audio_url:
        print(f"[跳过] 没找到音频: {title}")
        continue

    filename = safe_filename(title) + ".mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(filepath):
        print(f"[已存在] {filename}")
        continue

    print(f"\n[{i}/{len(entries)}] {title}")
    print(audio_url)

    temp_file = filepath + ".part"

    try:
        with session.get(
            audio_url,
            stream=True,
            timeout=60
        ) as r:

            r.raise_for_status()

            total = int(r.headers.get("content-length", 0))
            downloaded = 0

            with open(temp_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total:
                            percent = downloaded * 100 / total
                            print(
                                f"\r{percent:6.2f}% "
                                f"({downloaded / 1024 / 1024:.1f} MB)",
                                end=""
                            )

        os.replace(temp_file, filepath)
        print(f"\n完成: {filename}")

    except Exception as e:
        print(f"\n下载失败: {e}")

        if os.path.exists(temp_file):
            os.remove(temp_file)

        # 不因为单集失败而停止
        continue

    time.sleep(0.5)

print("\n全部处理完成。")