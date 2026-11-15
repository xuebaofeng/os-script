import os
import re
import subprocess

from utils import build_local_index, already_exists

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SONGS_FILE     = r"tbd.txt"
DOWNLOAD_DIR   = r"C:\BaiduNetdiskDownload"
ARCHIVE_FILE   = os.path.join(DOWNLOAD_DIR, "downloaded.txt")
LOCAL_LIBRARY  = r"C:\shared\media\CloudMusic"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name):
    for c in '<>:"/\\|?*':
        name = name.replace(c, "")
    return name

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print("Scanning local library...")
local_flat, local_entries = build_local_index(LOCAL_LIBRARY)
print(f"  {len(local_entries)} tracks indexed.\n")

with open(SONGS_FILE, "r", encoding="utf-8") as f:
    songs = [line.strip() for line in f if line.strip()]

for song in songs:
    # Strip accidental .opus suffix from song list entries
    song_base = re.sub(r"\.opus$", "", song, flags=re.IGNORECASE).strip()

    if already_exists(song_base, local_flat, local_entries):
        print(f"[SKIP] Already in local library: {song_base}")
        continue

    safe_name   = sanitize_filename(song_base)
    output_path = os.path.join(DOWNLOAD_DIR, f"{safe_name}.%(ext)s")

    # Prefer clean/official versions; ytsearch5 gives the filter room to skip bad hits
    search_url = f"ytsearch5:{song_base} clean official audio"

    cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--extractor-args", "youtube:player_client=android",
        "-x", "--audio-format", "opus", "--audio-quality", "0",
        "--no-overwrites",
        "--download-archive", ARCHIVE_FILE,
        "--embed-metadata",
        "--output", output_path,
        "--playlist-items", "1",
        "--match-filter",
        (
            "duration <= 600"
            " & title !*= 'live'"
            " & title !*= 'Live'"
            " & title !*= 'concert'"
            " & title !*= 'Concert'"
            " & title !*= 'MTV'"
            " & title !*= 'performance'"
            " & title !*= 'Performance'"
            " & title !*= 'acoustic'"
            " & title !*= 'Acoustic'"
            " & title !*= 'explicit'"
            " & title !*= 'Explicit'"
            " & title !*= '现场'"
        ),
        search_url,
    ]

    print(f"[DL] {song_base}")
    subprocess.run(cmd)
