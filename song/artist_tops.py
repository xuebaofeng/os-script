import os
import re
import requests
import unicodedata
from bs4 import BeautifulSoup


# =========================
# 基础配置
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

ARTISTS_URL = "https://kworb.net/spotify/artists.html"

MUSIC_DIR = r"C:\shared\media\CloudMusic"

TOP_N = 4       # 每个歌手提取前 N 首歌曲
ART_N = 400     # top artists


# =========================
# normalize
# =========================

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def norm_artist(s: str) -> str:
    """
    歌手名归一化：
    忽略大小写、空格、标点和重音符号。
    """
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()

    return re.sub(r"[^a-z0-9]", "", s)


def norm_song(s: str) -> str:
    """
    歌曲名归一化：
    忽略大小写、空格、标点和重音符号。
    """
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()

    return re.sub(r"[^a-z0-9]", "", s)


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

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"[FETCH] {url}")

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    r.raise_for_status()
    r.encoding = "utf-8"

    with open(path, "w", encoding="utf-8") as f:
        f.write(r.text)

    return r.text


# =========================
# 本地索引
# =========================

def build_local_index():
    index = set()

    if not os.path.isdir(MUSIC_DIR):
        print(f"[WARNING] music directory not found: {MUSIC_DIR}")
        return index

    for root, _, files in os.walk(MUSIC_DIR):
        for f in files:
            name = os.path.splitext(f)[0]
            index.add(norm(name))

    print(f"[LOCAL] songs loaded: {len(index)}")

    return index


# =========================
# clean song
# =========================

def clean_song(title: str) -> str:
    """
    清理歌曲名中的括号内容。
    不再按 ' - ' 截断，避免误删歌曲标题。
    """

    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)

    return re.sub(r"\s+", " ", title).strip()


# =========================
# 英文过滤
# =========================

def is_english(text: str) -> bool:
    cleaned = re.sub(r"[a-zA-Z\s\-']", "", text)

    return len(cleaned) == 0


# =========================
# blacklist
# =========================


def load_bad_words():
    path = os.path.join(BASE_DIR, "bad_words.txt")

    if not os.path.exists(path):
        print(f"[WARNING] blacklist not found: {path}")
        return {
            "artists": set(),
            "songs": set(),
            "artist_songs": set()
        }

    bad_list = {
        "artists": set(),
        "songs": set(),
        "artist_songs": set()
    }

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            # 歌曲规则：- Song
            if line.startswith("- "):
                song_key = norm_song(line[2:].strip())
                if song_key:
                    bad_list["songs"].add(song_key)
                else:
                    print(f"[WARNING] invalid blacklist rule: {line}")
                continue

            # 艺人规则：Artist -
            if line.endswith(" -"):
                artist_key = norm_artist(line[:-2].strip())
                if artist_key:
                    bad_list["artists"].add(artist_key)
                else:
                    print(f"[WARNING] invalid blacklist rule: {line}")
                continue

            # 指定艺人 + 歌曲：Artist - Song
            if " - " in line:
                artist, song = line.split(" - ", 1)
                artist_key = norm_artist(artist)
                song_key = norm_song(song)

                if artist_key and song_key:
                    bad_list["artist_songs"].add(
                        (artist_key, song_key)
                    )
                else:
                    print(f"[WARNING] invalid blacklist rule: {line}")
                continue

            print(f"[WARNING] invalid blacklist rule: {line}")

    return bad_list


def is_bad(artist: str, song: str, bad_list) -> bool:
    artist_key = norm_artist(artist)

    # 1. 排除整个艺人
    if artist_key in bad_list["artists"]:
        return True

    # 2. 提取歌曲标题各级前缀，支持 Remix、Featuring 等后缀
    parts = [p.strip() for p in song.split(" - ") if p.strip()]

    song_keys = {
        norm_song(" - ".join(parts[:i]))
        for i in range(1, len(parts) + 1)
    }

    # 3. 不限艺人的歌曲黑名单
    if song_keys & bad_list["songs"]:
        return True

    # 4. 指定艺人的歌曲黑名单
    for song_key in song_keys:
        if (artist_key, song_key) in bad_list["artist_songs"]:
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
# TOP N
# =========================

def parse_top_n(html, n=TOP_N):
    soup = BeautifulSoup(html, "html.parser")

    songs = []

    for a in soup.select("tr td:first-child a"):

        song = a.get_text(strip=True)

        if song:
            songs.append(song)

        if len(songs) >= n:
            break

    return songs


# =========================
# main
# =========================

def main():

    # 清空 tbd
    tbd_path = os.path.join(BASE_DIR, "tbd.txt")

    open(tbd_path, "w", encoding="utf-8").close()

    print("[RESET] tbd.txt cleared\n")

    # 获取歌手榜单
    html = get_cache(
        os.path.join(CACHE_DIR, "spotify_artists.html"),
        ARTISTS_URL
    )

    soup = BeautifulSoup(html, "html.parser")

    artist_list = build_artist_list(soup)

    # 本地歌曲索引
    local_index = build_local_index()

    # 黑名单
    bad_list = load_bad_words()

    print(f"[BAD] rules loaded: {len(bad_list)}")

    seen = set()

    print(f"\n[START] TOP {TOP_N}\n")

    with open(tbd_path, "a", encoding="utf-8") as out:

        for i, (artist, link) in enumerate(artist_list):

            if i >= ART_N:
                break

            print(f"[{i}] {artist}")

            url = "https://kworb.net" + link

            cache_file = os.path.join(
                CACHE_DIR,
                f"{safe_name(artist)}_spotify.html"
            )

            try:
                html = get_cache(cache_file, url)

            except requests.RequestException as e:
                print(f"   [ERROR] {artist}: {e}")
                continue

            songs = parse_top_n(html)

            if not songs:
                continue

            # 歌手必须英文
            if not is_english(artist):
                print(f"   SKIP artist (non-english): {artist}")
                continue

            for song in songs:

                song = clean_song(song)

                # 歌曲必须英文
                if not is_english(song):
                    print(f"   SKIP song (non-english): {song}")
                    continue

                line = f"{artist} - {song}"

                # 本地存在
                if norm(line) in local_index:
                    print(f"   SKIP (exists): {line}")
                    continue

                # 黑名单：歌手 + 歌名同时匹配
                if is_bad(artist, song, bad_list):
                    print(f"   SKIP (blacklist): {line}")
                    continue

                # 去重
                key = norm(line)

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

    with open(tbd_path, "r", encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip()]

    lines = sorted(set(lines), key=lambda x: x.lower())

    with open(tbd_path, "w", encoding="utf-8") as f:

        for x in lines:
            f.write(x + "\n")

    print("[DONE]")


if __name__ == "__main__":
    main()