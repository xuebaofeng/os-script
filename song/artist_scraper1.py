
import os
import re
import time
import hashlib
import requests
import unicodedata

from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# Configuration
# ============================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

ARTISTS_URL = "https://kworb.net/spotify/artists.html"

MUSIC_DIR = r"C:\shared\media\CloudMusic"

ARTISTS_FILE = "all_local_artists_sorted.txt"

OUTPUT_FILE = "tbd.txt"

BAD_WORDS_FILE = "bad_words.txt"  # All filtering rules are kept in this file


# Number of artists to process.
# 100 = first 100 artists
# 200 = first 200 artists
# None = all artists

ARTIST_LIMIT = 100


# Number of top songs per artist

TOP_N = 3


# Delay between requests (seconds)

REQUEST_DELAY = 0.5


# ============================================================
# HTTP Session
# ============================================================

session = requests.Session()

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(max_retries=retry)

session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update(HEADERS)


# ============================================================
# Cache
# ============================================================

def get_cache_path(url):

    key = hashlib.md5(
        url.encode("utf-8")
    ).hexdigest()

    return os.path.join(CACHE_DIR, key + ".html")


def get_html(url):

    cache_path = get_cache_path(url)

    if os.path.exists(cache_path):

        with open(
                cache_path,
                "r",
                encoding="utf-8"
        ) as f:

            return f.read()

    print(f"Downloading: {url}")

    response = session.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    response.encoding = response.apparent_encoding

    html = response.text

    with open(
            cache_path,
            "w",
            encoding="utf-8"
    ) as f:

        f.write(html)

    time.sleep(REQUEST_DELAY)

    return html


# ============================================================
# Text normalization
# ============================================================

def normalize(text):

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = text.encode(
        "ascii",
        "ignore"
    ).decode("ascii")

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]",
        "",
        text
    )

    return text


def clean_song_name(text):
    """Remove metadata/version suffixes for comparison.

    Examples:
      All Out of Love - Remastered -> All Out of Love
      Everybody - Radio Edit       -> Everybody
      Song (2011 Remaster)         -> Song

    This function is used for matching. Original scraped titles are retained
    for output to tbd.txt.
    """
    text = str(text or "").strip()

    # Remove bracketed annotations first.
    text = re.sub(r"\([^)]*\)|\[[^]]*\]|\{[^}]*\}", " ", text)

    # Remove common trailing release/version labels. Repeat to handle
    # combinations such as "Song - Remastered - Radio Edit".
    suffixes = [
        r"radio\s+edit", r"single\s+edit", r"album\s+version",
        r"single\s+version", r"radio\s+version", r"remaster(?:ed)?(?:\s+\d{4})?",
        r"\d{4}\s+remaster", r"extended\s+(?:mix|version|edit)",
        r"(?:original\s+)?(?:extended\s+)?mix", r"club\s+mix",
        r"dance\s+mix", r"instrumental(?:\s+version)?", r"acoustic(?:\s+version)?",
        r"karaoke(?:\s+version)?", r"explicit(?:\s+version)?",
        r"clean(?:\s+version)?", r"mono", r"stereo"
    ]
    suffix_pattern = re.compile(
        r"\s*(?:[-–—|:]\s*)?(?:" + "|".join(suffixes) + r")\s*$",
        re.IGNORECASE
    )
    previous = None
    while text != previous:
        previous = text
        text = suffix_pattern.sub("", text).strip(" -–—|:")

    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# English filtering
# ============================================================

def is_english(text):

    return bool(
        re.fullmatch(
            r"[a-zA-Z\s\-']+",
            text.strip()
        )
    )


# ============================================================
# Filtering rules: bad_words.txt ONLY
# ============================================================

def load_bad_words():
    """Read all exclusion rules from bad_words.txt.

    Supported formats:
      Artist Name -       block all songs by artist
      *word*               substring keyword match against artist/song
      Artist - Song        block one artist/song pair
      - Song               block this song title for every artist
      plain word           legacy bad-word filter (substring match)
    """
    blocked_artists = set()
    blocked_keywords = set()
    blocked_songs = set()
    blocked_song_titles = set()
    plain_words = set()

    if not os.path.exists(BAD_WORDS_FILE):
        print(f"Warning: {BAD_WORDS_FILE} not found; no filtering rules loaded")
        return blocked_artists, blocked_keywords, blocked_songs, blocked_song_titles, plain_words

    with open(BAD_WORDS_FILE, "r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("```"):
                continue

            if len(line) >= 3 and line.startswith("*") and line.endswith("*"):
                key = normalize(line[1:-1])
                if key:
                    blocked_keywords.add(key)
                continue

            title_match = re.fullmatch(r"-\s+(.+?)\s*", line)
            if title_match:
                key = normalize(clean_song_name(title_match.group(1)))
                if key:
                    blocked_song_titles.add(key)
                continue

            artist_match = re.fullmatch(r"(.+?)\s+-\s*", line)
            if artist_match:
                key = normalize(artist_match.group(1))
                if key:
                    blocked_artists.add(key)
                continue

            parts = re.split(r"\s+-\s+", line, maxsplit=1)
            if len(parts) == 2:
                artist_key = normalize(parts[0])
                song_key = normalize(clean_song_name(parts[1]))
                if artist_key and song_key:
                    blocked_songs.add((artist_key, song_key))
                continue

            # Backward-compatible plain word rule.
            key = normalize(line)
            if key:
                plain_words.add(key)

    print(f"Filtering rules loaded from {BAD_WORDS_FILE}:")
    print(f"  Artists       : {len(blocked_artists)}")
    print(f"  Keywords      : {len(blocked_keywords)}")
    print(f"  Artist + song : {len(blocked_songs)}")
    print(f"  Song titles   : {len(blocked_song_titles)}")
    print(f"  Plain words   : {len(plain_words)}")

    return blocked_artists, blocked_keywords, blocked_songs, blocked_song_titles, plain_words


def split_artist_credits(artist):
    parts = re.split(
        r"\s*(?:,|;|&|\bfeat\.?\b|\bft\.?\b|\bfeaturing\b|\bx\b)\s*",
        artist,
        flags=re.IGNORECASE
    )
    return [normalize(part) for part in parts if normalize(part)]


def blacklist_reason(artist, song, rules):
    blocked_artists, blocked_keywords, blocked_songs, blocked_song_titles, plain_words = rules
    artist_key = normalize(artist)
    song_key = normalize(clean_song_name(song))
    credits = set(split_artist_credits(artist))
    if artist_key:
        credits.add(artist_key)

    if credits.intersection(blocked_artists):
        return "artist"

    combined_text = normalize(f"{artist} {song}")
    if any(word in combined_text for word in blocked_keywords):
        return "keyword"
    if any(word in combined_text for word in plain_words):
        return "bad word"
    if song_key and song_key in blocked_song_titles:
        return "song title"
    if song_key and any((credit, song_key) in blocked_songs for credit in credits):
        return "artist + song"

    return None


# ============================================================
# Read artist list
# ============================================================

def load_artists(filename):

    artists = []

    if not os.path.exists(filename):

        raise FileNotFoundError(
            f"Artist list not found: {filename}"
        )

    with open(
            filename,
            "r",
            encoding="utf-8-sig"
    ) as f:

        for line in f:

            line = line.strip()

            # Format:
            # Bruno Mars: 18 songs

            match = re.match(
                r"^(.+?):\s*\d+\s+songs?$",
                line,
                re.IGNORECASE
            )

            if not match:
                continue

            artist = match.group(1).strip()

            if artist:
                artists.append(artist)

    return artists


# ============================================================
# Find artist URLs from Kworb
# ============================================================

def load_artist_urls():

    html = get_html(ARTISTS_URL)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    artist_urls = {}

    for a in soup.find_all("a", href=True):

        name = a.get_text(
            " ",
            strip=True
        )

        href = a["href"]

        if not name:
            continue

        if "artist/" not in href:
            continue

        url = urljoin(
            ARTISTS_URL,
            href
        )

        artist_urls[normalize(name)] = url

    return artist_urls


# ============================================================
# Get artist songs page URL
# ============================================================

def get_songs_url(artist_url):

    # Kworb artist page:
    # /spotify/artist/ARTIST_ID.html
    #
    # Songs page:
    # /spotify/artist/ARTIST_ID_songs.html

    if artist_url.endswith("_songs.html"):

        return artist_url

    if artist_url.endswith(".html"):

        return artist_url[:-5] + "_songs.html"

    return artist_url + "_songs.html"


# ============================================================
# Parse top N songs
# ============================================================

def parse_top_n(html, top_n):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    songs = []

    seen = set()

    for table in soup.find_all("table"):

        for row in table.find_all("tr"):

            cells = row.find_all("td")

            if not cells:
                continue

            # Song title is normally in the first column

            a = cells[0].find("a")

            if not a:
                continue

            song = a.get_text(
                " ",
                strip=True
            )

            song = clean_song_name(song)

            if not song:
                continue

            key = normalize(song)

            if not key or key in seen:
                continue

            seen.add(key)

            songs.append(song)

            if len(songs) >= top_n:

                return songs

    return songs


# ============================================================
# Scan local music library
# ============================================================

def load_local_songs():

    print("\nScanning local music library...")

    local_songs = set()

    local_pairs = set()

    if not os.path.isdir(MUSIC_DIR):

        raise FileNotFoundError(
            f"Music directory not found: {MUSIC_DIR}"
        )

    extensions = {
        ".mp3",
        ".flac",
        ".m4a",
        ".aac",
        ".wav",
        ".ogg",
        ".wma",
        ".opus"
    }

    count = 0

    for root, dirs, files in os.walk(MUSIC_DIR):

        for filename in files:

            path = Path(filename)

            if path.suffix.lower() not in extensions:
                continue

            count += 1

            stem = path.stem

            # Remove parentheses and brackets

            cleaned = clean_song_name(stem)

            normalized = normalize(cleaned)

            if normalized:
                local_songs.add(normalized)

            # Support both:
            # Artist - Song
            # Song - Artist

            parts = re.split(
                r"\s+-\s+",
                cleaned,
                maxsplit=1
            )

            if len(parts) == 2:

                left = normalize(parts[0])
                right = normalize(parts[1])

                if left and right:

                    local_pairs.add(
                        (left, right)
                    )

                    local_pairs.add(
                        (right, left)
                    )

    print(
        f"Found {count} local audio files"
    )

    return local_songs, local_pairs


# ============================================================
# Check whether song already exists
# ============================================================

def song_exists(
        artist,
        song,
        local_songs,
        local_pairs
):

    artist_key = normalize(artist)

    song_key = normalize(clean_song_name(song))

    if not artist_key or not song_key:
        return False

    # Match artist + song filename

    if (artist_key, song_key) in local_pairs:
        return True

    # Match common filename formats

    combined = artist_key + song_key

    for local in local_songs:

        if local == combined:
            return True

    return False


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("Kworb Artist Song Scraper")
    print("=" * 60)

    print(f"Artist limit : {ARTIST_LIMIT}")
    print(f"Top N songs  : {TOP_N}")
    print(f"Music folder : {MUSIC_DIR}")

    # --------------------------------------------------------
    # Load artists
    # --------------------------------------------------------

    artists = load_artists(
        ARTISTS_FILE
    )

    print(
        f"\nTotal artists in list: {len(artists)}"
    )

    if ARTIST_LIMIT is not None:

        artists = artists[:ARTIST_LIMIT]

    print(
        f"Artists to process: {len(artists)}"
    )

    # --------------------------------------------------------
    # Load blacklist
    # --------------------------------------------------------

    filtering_rules = load_bad_words()

    # --------------------------------------------------------
    # Scan local music
    # --------------------------------------------------------

    local_songs, local_pairs = load_local_songs()

    # --------------------------------------------------------
    # Load Kworb artist index
    # --------------------------------------------------------

    print("\nLoading Kworb artist index...")

    artist_urls = load_artist_urls()

    print(
        f"Artists found on Kworb: {len(artist_urls)}"
    )

    # --------------------------------------------------------
    # Process artists
    # --------------------------------------------------------

    results = set()
    result_keys = set()

    stats = {
        "processed": 0,
        "not_found": 0,
        "songs_found": 0,
        "existing": 0,
        "non_english": 0,
        "blacklisted": 0,
        "added": 0,
        "errors": 0
    }

    for index, artist in enumerate(
            artists,
            start=1
    ):

        print(
            f"\n[{index}/{len(artists)}] {artist}"
        )

        stats["processed"] += 1

        # ----------------------------------------------------
        # English artist filter
        # ----------------------------------------------------

        if not is_english(artist):

            print("  Skip: non-English artist")

            stats["non_english"] += 1

            continue

        artist_rule = blacklist_reason(artist, "", filtering_rules)
        if artist_rule == "artist":
            print("  Skip: blacklisted artist")
            stats["blacklisted"] += 1
            continue

        # ----------------------------------------------------
        # Find artist URL
        # ----------------------------------------------------

        artist_url = artist_urls.get(
            normalize(artist)
        )

        if not artist_url:

            print("  Artist not found on Kworb")

            stats["not_found"] += 1

            continue

        songs_url = get_songs_url(
            artist_url
        )

        # ----------------------------------------------------
        # Download / load songs page
        # ----------------------------------------------------

        try:

            html = get_html(songs_url)

            songs = parse_top_n(
                html,
                TOP_N
            )

        except Exception as e:

            print(
                f"  Error: {e}"
            )

            stats["errors"] += 1

            continue

        print(
            f"  Songs retrieved: {len(songs)}"
        )

        stats["songs_found"] += len(songs)

        # ----------------------------------------------------
        # Filter songs
        # ----------------------------------------------------

        for song in songs:

            if not is_english(song):

                stats["non_english"] += 1

                continue

            reason = blacklist_reason(artist, song, filtering_rules)
            if reason:
                print(f"  Blacklisted ({reason}): {song}")
                stats["blacklisted"] += 1
                continue

            # Check local library

            if song_exists(
                    artist,
                    song,
                    local_songs,
                    local_pairs
            ):

                print(
                    f"  Existing: {song}"
                )

                stats["existing"] += 1

                continue

            line = f"{artist} - {song}"

            # Deduplicate

            key = normalize(line)

            if not key:
                continue

            if key in result_keys:
                continue

            results.add(line)
            result_keys.add(key)

            print(
                f"  + {song}"
            )

            stats["added"] += 1

    # --------------------------------------------------------
    # Write output
    # --------------------------------------------------------

    sorted_results = sorted(
        results,
        key=lambda x: normalize(x)
    )

    with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
    ) as f:

        for line in sorted_results:

            f.write(
                line + "\n"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("Finished")
    print("=" * 60)

    for key, value in stats.items():

        print(
            f"{key:15}: {value}"
        )

    print("-" * 60)

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Total new songs: {len(sorted_results)}"
    )


if __name__ == "__main__":

    main()

