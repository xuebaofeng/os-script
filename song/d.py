import os
import subprocess

# Paths
songs_file = r"spotify_us_top100_unique.txt"  # your songs list
download_folder = r"C:\BaiduNetdiskDownload"
archive_file = os.path.join(download_folder, "downloaded.txt")

# Read songs list
with open(songs_file, "r", encoding="utf-8") as f:
    songs = [line.strip() for line in f if line.strip()]

# Function to sanitize filename
def sanitize_filename(name):
    illegal_chars = '<>:"/\\|?*'
    for c in illegal_chars:
        name = name.replace(c, '')
    return name

# Generate and run yt-dlp commands
for song in songs:
    # remove .opus suffix if present for output template
    if song.lower().endswith(".opus"):
        song_base = song[:-5].strip()
    else:
        song_base = song

    safe_name = sanitize_filename(song_base)

    # yt-dlp URL: use ytsearch1 to search YouTube for the song
    url = f"ytsearch1:{song}"

    # Output template: force the file to the exact name from songs.txt
    output_path = os.path.join(download_folder, f"{safe_name}.%(ext)s")

    # Build yt-dlp command
    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "opus", "--audio-quality", "0",
        "--no-overwrites",
        "--download-archive", archive_file,
        "--embed-metadata",
        "--output", output_path,
        url,
        "--match-filter", "duration <= 600"
    ]

    print("Running command:", " ".join(cmd))
    subprocess.run(cmd)
