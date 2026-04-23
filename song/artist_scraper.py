import os
import re
import requests
from bs4 import BeautifulSoup
import extract_artists

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

MUSIC_DIRS = [
    r"C:\shared\media\CloudMusic",
    r"C:\BaiduNetdiskDownload"
]

not_found_artists = []

# =========================
# cache helper
# =========================
def get_cache(name, url):
    path = os.path.join(CACHE_DIR, name)

    if os.path.exists(path):
        print(f"[CACHE] {name}")
        return open(path, "r", encoding="utf-8").read()

    print(f"[FETCH] {name}")
    r = requests.get(url, headers=HEADERS)
    r.encoding = "utf-8"

    with open(path, "w", encoding="utf-8") as f:
        f.write(r.text)

    return r.text


# =========================
# normalize
# =========================
def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


# =========================
# artist cache key（🔥关键）
# =========================
def artist_key(artist):
    return re.sub(r"\W+", "_", artist.lower()).strip("_")


# =========================
# clean title
# =========================
def clean_title(t):
    t = t.replace("â", "'")

    # 去掉括号
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\[.*?\]", "", t)

    # 🔥 核心：只取第一个 "-"
    t = t.split(" - ")[0].strip()

    # 再清理多余空格
    t = re.sub(r"\s+", " ", t).strip()

    return t


# =========================
# clean local filename
# =========================
def clean_song_name(filename):
    name = os.path.splitext(filename)[0]
    name = name.replace("â", "'")

    if " - " in name:
        name = name.split(" - ", 1)[1]

    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\[.*?\]", "", name)

    return norm(name)


# =========================
# local index
# =========================
def build_music_index():
    index = set()

    for d in MUSIC_DIRS:
        if not os.path.exists(d):
            continue

        for root, _, files in os.walk(d):
            for f in files:
                index.add(clean_song_name(f))

    return index


# =========================
# bad words
# =========================
def load_bad_words():
    path = "bad_words.txt"
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


def is_bad(artist, song, bad_list):
    full = f"{artist.lower()} - {song.lower()}"

    for b in bad_list:
        if b == full:
            return True
        if full.startswith(b):
            return True

    return False


# =========================
# build artist index
# =========================
def build_artist_index(soup):
    index = {}

    for a in soup.select("tr td.text a"):
        name = norm(a.get_text())
        link = a.get("href")

        if name and link:
            index[name] = link

    print(f"🎯 Artist index built: {len(index)}")
    return index


# =========================
# 获取歌曲（🔥缓存兼容版）
# =========================
def get_spotify_songs(artist, artist_index):
    target = norm(artist)
    link = artist_index.get(target)

    print("DEBUG link =", link)

    if not link:
        print(f"❌ NOT FOUND: {artist}")
        not_found_artists.append(artist)
        return []

    base = artist_key(artist)

    # 兼容旧缓存 + 新缓存
    candidates = [
        f"{base}_spotify.html",
        f"{base}_spotify_songs.html"
    ]

    html = None

    for name in candidates:
        path = os.path.join(CACHE_DIR, name)
        if os.path.exists(path):
            print(f"[CACHE] {name}")
            html = open(path, "r", encoding="utf-8").read()
            break

    # 没命中才抓
    if html is None:
        url = "https://kworb.net" + link
        print("[FETCH]", artist)

        html = requests.get(url, headers=HEADERS).text

        path = os.path.join(CACHE_DIR, candidates[0])
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    soup = BeautifulSoup(html, "html.parser")

    songs = [
        clean_title(a.get_text(strip=True))
        for a in soup.select("tr td:first-child a")[:3]
    ]

    return songs


# =========================
# load artists
# =========================
def load_artists():
    with open("all_artists.txt", "r", encoding="utf-8") as f:
        return [x.strip() for x in f if x.strip()]


# =========================
# main
# =========================
def main():
    print("\n📥 load spotify artists (once)")

    html = get_cache(
        "spotify_artists.html",
        "https://kworb.net/spotify/artists.html"
    )

    soup = BeautifulSoup(html, "html.parser")
    artist_index = build_artist_index(soup)

    artists = load_artists()
    local_index = build_music_index()
    bad_list = load_bad_words()

    print(f"\n🎤 artists: {len(artists)}")
    print(f"📀 local songs: {len(local_index)}")
    print(f"🚫 bad rules: {len(bad_list)}")

    tbd = []

    for artist in artists:
        print(f"\n🎧 {artist}")

        songs = get_spotify_songs(artist, artist_index)

        for s in songs:
            key = norm(s.split(" - ")[-1])

            # 本地存在
            if key in local_index:
                continue

            # bad filter
            if is_bad(artist, s, bad_list):
                print(f"SKIP (bad): {s}")
                continue

            if " - " in s:
                line = s
            else:
                line = f"{artist} - {s}"

            tbd.append(line)

    # 去重 + 排序
    unique = {}
    for x in tbd:
        k = x.lower()
        if k not in unique:
            unique[k] = x

    final = sorted(unique.values(), key=lambda x: x.lower())

    if final:
        with open("tbd.txt", "w", encoding="utf-8") as f:
            for x in final:
                f.write(x + "\n")

        print("\n📄 tbd.txt generated")
    else:
        print("\n✅ nothing to write")

    with open("not_found.txt", "w", encoding="utf-8") as f:
        for artist in sorted(set(not_found_artists)):
            f.write(artist + "\n")

        print(f"\n📝 saved {len(set(not_found_artists))} artists to not_found.txt")


if __name__ == "__main__":
    main()