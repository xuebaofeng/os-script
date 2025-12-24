import requests
import os

urls = [
    "https://kworb.net/spotify/country/us_daily.html",
    "https://kworb.net/spotify/country/us_daily_totals.html",
    "https://kworb.net/spotify/country/us_weekly.html",
    "https://kworb.net/spotify/country/us_weekly_totals.html",
    "https://kworb.net/radio",
]


cache_dir = "html_cache"
os.makedirs(cache_dir, exist_ok=True)

for url in urls:
    filename = os.path.join(cache_dir, url.split("/")[-1])

    if not os.path.exists(filename):
        print(f"Downloading {url} ...")
        resp = requests.get(url)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(resp.text)
    else:
        print(f"Cached file exists: {filename}")


from bs4 import BeautifulSoup
import os
import re


all_songs = []

for url in urls:
    file = os.path.join(url.split("/")[-1])
    filepath = os.path.join(cache_dir, file)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    table = soup.find("table")
    if not table:
        continue

    rows = table.find_all("tr")[1:101]  # 前100条
    for row in rows:
        tds = row.find_all("td")
        if len(tds) >= 3:
            third_td = tds[2]

            # 优先 Spotify 风格 <a> 标签
            a_tags = third_td.find_all("a")
            if len(a_tags) >= 2:
                artist = a_tags[0].get_text(strip=True)
                title = a_tags[1].get_text(strip=True)
                song = f"{artist} - {title}"

            # 如果没有 <a> 标签，尝试 Radio 风格 <div>
            else:
                div = third_td.find("div")
                if div:
                    song = div.get_text(strip=True)
                else:
                    continue  # 没有找到歌曲信息，跳过

            # 清理格式：去掉换行、多余空格
            song = " ".join(song.split())
            # 去掉括号及内容
            song = re.sub(r'\s*\(.*?\)', '', song)

            all_songs.append(song)


# 去重
unique_songs = list(dict.fromkeys(all_songs))



music_dir = r"C:\shared\media\CloudMusic"
existing_files = set(os.listdir(music_dir))  # 获取目录下所有文件名

# 去掉已有文件的扩展名并统一小写
existing_files_no_ext = set(os.path.splitext(f)[0].lower() for f in existing_files)

# 假设已经生成了 unique_songs 列表
# unique_songs = ["Brenda Lee - Rockin' Around The Christmas Tree", ...]

songs_to_download = []

for song in unique_songs:
    # 只考虑歌曲名，不加后缀
    if song.lower() not in existing_files_no_ext:
        songs_to_download.append(song)

print(f"{len(songs_to_download)} songs need to be downloaded.")



import re

# 常见脏词列表
bad_words = []
with open("bad_words.txt", "r", encoding="utf-8") as f:
    bad_words = [line.strip() for line in f]

def is_family_friendly(song):
    # 转小写检查脏词
    song_lower = song.lower()
    for word in bad_words:
        if word.lower() in song_lower:
            return False

    # 可以加更多规则，比如排除 rap / trap 风格
    if re.search(r'\brap\b|\btrap\b', song_lower):
        return False

    # 可扩展规则：根据年份、歌手、已知列表等
    return True

# 筛选家庭友好歌曲
family_songs = [s for s in songs_to_download if is_family_friendly(s)]

print(f"{len(family_songs)} songs are family friendly out of {len(family_songs)}")

family_songs = sorted(set(family_songs))  # 去重并按字母顺序排序


# 保存 TXT
with open("spotify_us_top100_unique.txt", "w", encoding="utf-8") as f:
    for song in family_songs:
        f.write(f"{song}\n")

print(f"Done! {len(family_songs)} unique songs saved.")
