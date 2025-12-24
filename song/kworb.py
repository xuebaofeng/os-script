import os
import re

import requests
from bs4 import BeautifulSoup


import re


URL = "https://kworb.net/pop/cumulative.html"
OUTPUT_FILE = "kworb.txt"
LIMIT = 100

MUSIC_DIR = r"C:\shared\media\CloudMusic"

AUDIO_EXTS = {".mp3", ".flac", ".opus", ".m4a", ".aac", ".wav"}

headers = {
    "User-Agent": "Mozilla/5.0"
}

resp = requests.get(URL, headers=headers, timeout=15)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "lxml")

songs = []

def clean_feat(text: str) -> str:
    """
    去掉歌曲名或歌手里的 (feat. XXX) / (ft. XXX) / (featuring XXX)
    """
    text = re.sub(r"\(.*?(feat|ft|featuring).*?\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(feat|ft|featuring)\s+.*$", "", text, flags=re.IGNORECASE)
    return text.strip()

def clean_parentheses(text: str) -> str:
    """
    去掉所有圆括号及其中内容，例如:
    "Song Name (Live)" -> "Song Name"
    """
    text = re.sub(r"\(.*?\)", "", text)
    # 去掉多余空格或 - 号
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("-")
    return text.strip()

for row in soup.select("table tbody tr"):
    if len(songs) >= LIMIT:
        break

    cols = row.find_all("td")
    if len(cols) < 2:
        continue

    raw = cols[1].get_text(strip=True)

    # 确保格式：歌手 - 歌名
    if " - " in raw:
        artist, title = raw.split(" - ", 1)
        artist = clean_parentheses(artist)
        title = clean_parentheses(title)
        songs.append(f"{artist.strip()} - {title.strip()}")

# 去重（保持顺序）
songs = list(dict.fromkeys(songs))

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(songs))

print(f"已生成前 {len(songs)} 首歌曲 -> {OUTPUT_FILE}")




def normalize(name: str) -> str:
    name = name.lower()

    # 1️⃣ 去掉 (feat. xxx) / (ft. xxx) / (featuring xxx)
    name = re.sub(r"\(\s*(feat|ft|featuring)\.?.*?\)", "", name)

    # 2️⃣ 去掉非括号形式： feat. xxx / ft xxx
    name = re.sub(r"\s+(feat|ft|featuring)\.?\s+.*$", "", name)

    # 3️⃣ 清理多余空格和符号
    name = re.sub(r"\s+", " ", name)
    name = name.strip(" -_")

    return name.strip()

# 1. 扫描本地已有歌曲
local_songs = set()

for root, _, files in os.walk(MUSIC_DIR):
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in AUDIO_EXTS:
            base = os.path.splitext(file)[0]
            local_songs.add(normalize(base))

print(f"本地歌曲（归一化后）数量: {len(local_songs)}")

# 2. 读取 kworb 列表
with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    kworb_songs = [line.strip() for line in f if line.strip()]

# 3. 去重
remaining = []
removed = 0

for song in kworb_songs:
    if normalize(song) not in local_songs:
        remaining.append(song)
    else:
        removed += 1

# 4. 写入结果
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(remaining))

print(f"已剔除已存在歌曲: {removed}")
print(f"剩余待下载歌曲: {len(remaining)}")
print(f"输出文件: {OUTPUT_FILE}")



# ❌ 关键词黑名单（可自行加）
BAD_KEYWORDS = {
    "fuck", "shit", "bitch", "nigga", "pussy", "dick",
    "sex", "sexy", "naked", "horny", "booty", "twerk",
    "drug", "cocaine", "weed", "lean", "kill", "murder", "gun",
    "explicit"
}

# ❌ 高风险艺人（rap / trap）
BAD_ARTISTS = {
    "drake", "kanye west", "travis scott", "cardi b",
    "nicki minaj", "future", "kendrick lamar",
    "21 savage", "lil", "post malone"
}

def normalize(text: str) -> str:
    text = text.lower()

    # 去 feat
    text = re.sub(r"\(.*?(feat|ft|featuring).*?\)", "", text)
    text = re.sub(r"\s+(feat|ft|featuring)\s+.*$", "", text)

    # 只保留字母数字空格
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def is_family_friendly(song: str) -> bool:
    norm = normalize(song)

    # 拆分 artist / title
    if " - " in song:
        artist, title = song.split(" - ", 1)
        artist = normalize(artist)
        title = normalize(title)
    else:
        artist = ""
        title = norm

    # 1️⃣ 关键词过滤
    for bad in BAD_KEYWORDS:
        if bad in title or bad in norm:
            return False

    # 2️⃣ 艺人黑名单
    for bad_artist in BAD_ARTISTS:
        if bad_artist in artist:
            return False

    return True



friendly = [s for s in remaining if is_family_friendly(s)]

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(friendly))

print(f"输入歌曲数: {len(songs)}")
print(f"家庭友好歌曲数: {len(friendly)}")
print(f"输出文件: {OUTPUT_FILE}")

