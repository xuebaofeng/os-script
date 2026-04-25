import os
import re
import requests
import unicodedata
from bs4 import BeautifulSoup

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

ARTISTS_URL = "https://kworb.net/spotify/artists.html"

MUSIC_DIR = r"C:\shared\media\CloudMusic"


# =========================
# normalize
# =========================
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


# =========================
# safe filename
# =========================
def safe_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip()


# =========================
# cache
# =========================
def get_cache(path, url):
    if os.path.exists(path):
        print(f"[CACHE] {os.path.basename(path)}")
        return open(path, "r", encoding="utf-8").read()

    print(f"[FETCH] {url}")
    r = requests.get(url, headers=HEADERS)
    r.encoding = "utf-8"

    with open(path, "w", encoding="utf-8") as f:
        f.write(r.text)

    return r.text


# =========================
# 本地索引
# =========================
def build_local_index():
    index = set()

    for root, _, files in os.walk(MUSIC_DIR):
        for f in files:
            name = os.path.splitext(f)[0]
            index.add(norm(name))   # "artist - song"

    print(f"[LOCAL] songs loaded: {len(index)}")
    return index


# =========================
# clean song
# =========================
def clean_song(title: str) -> str:
    # 去括号
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)

    # 只保留第一个 "-"
    parts = [p.strip() for p in title.split(" - ")]
    return parts[0].strip()


# =========================
# 英文过滤
# =========================
def is_english(text: str) -> bool:
    cleaned = re.sub(r"[a-zA-Z\s\-']", "", text)
    return len(cleaned) == 0


# =========================
# bad words（前缀匹配）
# =========================
def load_bad_words():
    path = "bad_words.txt"

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return [norm(x) for x in f if x.strip()]


def is_bad(line: str, bad_list) -> bool:
    line = norm(line)

    for b in bad_list:
        if line == b:
            return True
        if line.startswith(b):   # ✅ 前缀匹配
            return True

    return False


# =========================
# artist list（保序）
# =========================
def build_artist_list(soup):
    artists = []

    for a in soup.select("tr td.text a"):
        name = a.get_text(strip=True)
        link = a.get("href")

        if name and link:
            artists.append((name, link))

    print(f"[INFO] artists loaded: {len(artists)}")
    return artists


# =========================
# TOP1
# =========================
def parse_top1(html):
    soup = BeautifulSoup(html, "html.parser")
    a = soup.select_one("tr td:first-child a")
    return a.get_text(strip=True) if a else None


# =========================
# main
# =========================
def main():

    # 清空 tbd
    open("tbd.txt", "w", encoding="utf-8").close()
    print("[RESET] tbd.txt cleared\n")

    html = get_cache(
        os.path.join(CACHE_DIR, "spotify_artists.html"),
        ARTISTS_URL
    )

    soup = BeautifulSoup(html, "html.parser")
    artist_list = build_artist_list(soup)

    local_index = build_local_index()

    bad_list = load_bad_words()
    print(f"[BAD] rules loaded: {len(bad_list)}")

    seen = set()

    print("\n[START]\n")

    with open("tbd.txt", "a", encoding="utf-8") as out:

        for i, (artist, link) in enumerate(artist_list):
            if i > 1000:
                break

            print(f"[{i}] {artist}")

            url = "https://kworb.net" + link

            cache_file = os.path.join(
                CACHE_DIR,
                f"{safe_name(artist)}_spotify.html"
            )

            html = get_cache(cache_file, url)

            song = parse_top1(html)
            if not song:
                continue

            song = clean_song(song)



            # ❌ 歌曲必须英文
            if not is_english(song):
                print(f"   SKIP song (non-english): {song}")
                continue

            # ❌ 歌手必须英文
            if not is_english(artist):
                print(f"   SKIP artist (non-english): {artist}")
                continue

            line = f"{artist} - {song}"
            key = norm(line)

            # 本地存在
            if key in local_index:
                print(f"   SKIP (exists): {line}")
                continue

            # bad filter（前缀）
            if is_bad(line, bad_list):
                print(f"   SKIP (bad): {line}")
                continue

            # 去重
            if key in seen:
                continue

            seen.add(key)

            print(f"   WRITE: {line}")

            out.write(line + "\n")
            out.flush()

    # =========================
    # 最后排序
    # =========================
    print("\n[SORT] fixing order...")

    with open("tbd.txt", "r", encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip()]

    lines = sorted(set(lines), key=lambda x: x.lower())

    with open("tbd.txt", "w", encoding="utf-8") as f:
        for x in lines:
            f.write(x + "\n")

    print("[DONE]")


if __name__ == "__main__":
    main()