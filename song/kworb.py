import os
import re
import time
import requests
from bs4 import BeautifulSoup

from utils import build_local_index, already_exists, split_artists

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

URLS = [
    "https://kworb.net/spotify/country/us_daily.html",
    "https://kworb.net/spotify/country/us_daily_totals.html",
    "https://kworb.net/spotify/country/us_weekly.html",
    "https://kworb.net/spotify/country/us_weekly_totals.html",
    "https://kworb.net/radio",
    "https://kworb.net/pop/cumulative.html",
]

CACHE_DIR = "cache"
CACHE_TTL = 7 * 24 * 3600  # seconds; re-download if older than this
TOP_N = 100            # rows to take per page
LOCAL_LIBRARY = r"C:\shared\media\CloudMusic"
BAD_WORDS_FILE = "bad_words.txt"
OUTPUT_FILE = "tbd.txt"

os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Step 1: Download / refresh cache
# ---------------------------------------------------------------------------

def cache_path(url):
    return os.path.join(CACHE_DIR, url.split("/")[-1] or "index.html")

def fetch(url):
    path = cache_path(url)
    age = time.time() - os.path.getmtime(path) if os.path.exists(path) else float("inf")
    if age < CACHE_TTL:
        print(f"[cache] {path}")
        return
    print(f"[download] {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "w", encoding="utf-8") as f:
        f.write(resp.text)

for url in URLS:
    fetch(url)

# ---------------------------------------------------------------------------
# Step 2: Parse pages
# ---------------------------------------------------------------------------

def clean_text(text):
    """Normalise whitespace and fix common encoding artifacts."""
    text = " ".join(text.split())
    # Fix mojibake: text was decoded as latin-1 but is actually utf-8
    try:
        text = text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    # Strip control characters
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    return text.strip()

def parse_page(url):
    """Return a list of 'Artist - Title' strings from a kworb page."""
    path = cache_path(url)
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    table = soup.find("table")
    if not table:
        print(f"[warn] no table in {path}")
        return []

    songs = []
    for row in table.find_all("tr")[1 : TOP_N + 1]:
        a_tags = row.find_all("a")

        if len(a_tags) >= 2:
            # Spotify-style pages: first <a> = artist, second <a> = title
            artist = clean_text(a_tags[0].get_text())
            title  = clean_text(a_tags[1].get_text())
            song   = f"{artist} - {title}"
        else:
            # Radio / cumulative: song string is inside a <div>
            div = row.find("div")
            if not div:
                continue
            song = clean_text(div.get_text())

        # Drop parenthetical suffixes like "(feat. X)", "(Remix)", "(Live)"
        song = re.sub(r"\s*\(.*?\)", "", song).strip()

        if " - " not in song:
            continue  # skip malformed rows

        songs.append(song)

    return songs

all_songs = []
for url in URLS:
    found = parse_page(url)
    print(f"  {len(found):3d} songs from {url.split('/')[-1]}")
    all_songs.extend(found)

# Deduplicate while preserving first-seen order
unique_songs = list(dict.fromkeys(all_songs))
print(f"\n{len(unique_songs)} unique songs across all pages.")

# ---------------------------------------------------------------------------
# Step 3: Filter out songs already in local library
# ---------------------------------------------------------------------------

print(f"\nScanning local library: {LOCAL_LIBRARY}")
local_flat, local_entries = build_local_index(LOCAL_LIBRARY)
print(f"  {len(local_entries)} tracks indexed.")

songs_to_download = [s for s in unique_songs if not already_exists(s, local_flat, local_entries)]
print(f"  {len(unique_songs) - len(songs_to_download)} already present, "
      f"{len(songs_to_download)} to download.")

# ---------------------------------------------------------------------------
# Step 4: Family-friendly filter
# ---------------------------------------------------------------------------

with open(BAD_WORDS_FILE, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

blocked_artists  = set()  # artist name only — block all their songs
blocked_songs    = set()  # exact "Artist - Title" matches
blocked_keywords = []     # *keyword* — block if song string contains this

for line in lines:
    if line.startswith("*") and line.endswith("*"):
        blocked_keywords.append(line[1:-1].lower())
    elif " - " in line:
        blocked_songs.add(line.lower())
    else:
        blocked_artists.add(line.lower())

def is_clean(song):
    song_lower = song.lower()
    # Split "Artist1 & Artist2 - Title" and check each artist individually
    if " - " in song_lower:
        artist_str, _ = song_lower.split(" - ", 1)
        # Check raw artist string first (handles names with commas like "Tyler, The Creator")
        if artist_str.strip() in blocked_artists:
            return False
        artists = split_artists(artist_str)  # handles &, feat, x, / etc.
    else:
        artists = [song_lower]
    if any(a in blocked_artists for a in artists):
        return False
    if song_lower in blocked_songs:
        return False
    for kw in blocked_keywords:
        if kw in song_lower:
            return False
    return True

family_songs = []
skipped = 0

print(f"\nChecking {len(songs_to_download)} songs...")
for song in songs_to_download:
    if is_clean(song):
        family_songs.append(song)
    else:
        print(f"  [skip] {song}")
        skipped += 1

print(f"\n{len(family_songs)} clean songs to download ({skipped} filtered).")

family_songs = sorted(set(family_songs))

# ---------------------------------------------------------------------------
# Step 5: Write tbd.txt
# ---------------------------------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for song in family_songs:
        f.write(f"{song}\n")

print(f"\nWritten to {OUTPUT_FILE}.")
