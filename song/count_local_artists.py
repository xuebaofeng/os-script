import os
import re
from pathlib import Path
from collections import Counter

def extract_artist_from_filename(filename):
    """Extract artist name from filename using various patterns"""
    # Remove file extension
    name = Path(filename).stem
    
    # Replace special quotes
    name = name.replace("â", "'")
    
    # Pattern 1: "Artist - Song" format (most common)
    if " - " in name:
        artist_part = name.split(" - ", 1)[0]
    else:
        artist_part = name
    
    # Handle collaborations - take the first artist
    collaboration_separators = [" & ", " x ", " X ", " + ", ", ", " ft ", " Ft ", " FT "]
    for sep in collaboration_separators:
        if sep in artist_part:
            artist_part = artist_part.split(sep)[0]
    
    # Clean up the artist name
    artist = re.sub(r'\s+', ' ', artist_part.strip())
    
    # Remove common prefixes/suffixes that aren't artist names
    prefixes_to_remove = ['01 ', '02 ', '03 ', '04 ', '05 ', '06 ', '07 ', '08 ', '09 ', '10 ']
    for prefix in prefixes_to_remove:
        if artist.startswith(prefix):
            artist = artist[len(prefix):]
    
    return artist if len(artist) > 1 else None

def count_local_artists(music_directories):
    """Count songs per artist in local music directories"""
    music_extensions = {'.mp3', '.opus', '.flac', '.wav', '.m4a', '.aac'}
    artist_song_count = Counter()
    total_files = 0
    
    for directory in music_directories:
        if not os.path.exists(directory):
            print(f"Directory not found: {directory}")
            continue
            
        print(f"Scanning directory: {directory}")
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in music_extensions:
                    total_files += 1
                    artist = extract_artist_from_filename(file)
                    if artist:
                        artist_song_count[artist] += 1
    
    return artist_song_count, total_files

def main():
    # Music directories from the original scraper
    music_directories = [
        r"C:\shared\media\CloudMusic",
    ]
    
    print("Analyzing local music files...")
    artist_counts, total_files = count_local_artists(music_directories)
    
    print(f"\nTotal music files found: {total_files}")
    print(f"Unique artists found: {len(artist_counts)}")
    
    # Sort all artists by song count descending
    sorted_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n=== Top 100 artists sorted by song count ===")
    for i, (artist, count) in enumerate(sorted_artists[:100], 1):
        print(f"{i:3d}. {artist}: {count} songs")
    
    # Find artists with >10 songs
    artists_over_10 = {artist: count for artist, count in artist_counts.items() if count > 10}
    
    print(f"\n=== Artists with >10 songs: {len(artists_over_10)} ===")
    if artists_over_10:
        over_10_sorted = sorted(artists_over_10.items(), key=lambda x: x[1], reverse=True)
        for i, (artist, count) in enumerate(over_10_sorted, 1):
            print(f"{i:2d}. {artist}: {count} songs")
        
        # Save results to file
        with open("local_artists_over_10.txt", "w", encoding="utf-8") as f:
            f.write(f"Local artists with more than 10 songs ({len(over_10_sorted)} total):\n")
            f.write("=" * 60 + "\n\n")
            for artist, count in over_10_sorted:
                f.write(f"{artist}: {count} songs\n")
        
        print(f"\nResults saved to: local_artists_over_10.txt")
    
    # Save all artists to file
    with open("all_local_artists_sorted.txt", "w", encoding="utf-8") as f:
        f.write(f"All local artists sorted by song count ({len(sorted_artists)} total):\n")
        f.write("=" * 60 + "\n\n")
        for artist, count in sorted_artists:
            f.write(f"{artist}: {count} songs\n")
    
    print(f"All artists saved to: all_local_artists_sorted.txt")

if __name__ == "__main__":
    main()
