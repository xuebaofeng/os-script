import os
import re
from pathlib import Path

def extract_artists(directory):
    """Extract unique artist names from music files in a directory"""
    artists = set()
    
    # Music file extensions
    music_extensions = {'.mp3', '.opus', '.flac', '.wav', '.m4a', '.aac'}
    
    # Pattern to match artist name before " - " in filename
    # This handles various formats like "Artist - Song.mp3" or "Artist - Song (remix).mp3"
    artist_pattern = re.compile(r'^([^:-]+?)\s*[-]\s*', re.IGNORECASE)
    
    # Special handling for featured artists and collaborations
    collab_patterns = [
        re.compile(r'^([^&]+?)\s*[&]\s*', re.IGNORECASE),  # Artist & Artist
        re.compile(r'^([^,]+?)\s*[,]\s*', re.IGNORECASE),  # Artist, Artist
        re.compile(r'^([^+]+?)\s*[+]\s*', re.IGNORECASE),  # Artist + Artist
        re.compile(r'^([^x]+?)\s*[x]\s*', re.IGNORECASE),  # Artist x Artist
    ]
    
    # Pattern to extract primary artist from collaborations
    primary_artist_pattern = re.compile(r'^([^,&+x]+)', re.IGNORECASE)
    
    def clean_artist_name(name):
        """Clean up artist name by removing extra spaces and special characters"""
        return re.sub(r'\s+', ' ', name.strip())
    
    def extract_primary_artist(filename):
        """Extract the primary artist from a filename"""
        # Try the standard "Artist - Song" pattern first
        match = artist_pattern.match(filename)
        if match:
            artist_name = clean_artist_name(match.group(1))
            
            # Handle collaborations - take the first artist as primary
            primary_match = primary_artist_pattern.match(artist_name)
            if primary_match:
                return clean_artist_name(primary_match.group(1))
            return artist_name
        
        # Try collaboration patterns
        for pattern in collab_patterns:
            match = pattern.match(filename)
            if match:
                artist_name = clean_artist_name(match.group(1))
                return artist_name
        
        # If no pattern matches, use the first word or return None
        parts = filename.split()
        if len(parts) > 0:
            return clean_artist_name(parts[0])
        return None
    
    # Walk through the directory
    for file_path in Path(directory).iterdir():
        if file_path.is_file() and file_path.suffix.lower() in music_extensions:
            filename = file_path.name
            artist = extract_primary_artist(filename)
            if artist and len(artist) > 1:  # Exclude single characters
                artists.add(artist)
    
    return sorted(list(artists))

def main():
    music_directory = r"C:\shared\media\CloudMusic"
    
    print("Extracting artists from music files...")
    artists = extract_artists(music_directory)
    
    print(f"Found {len(artists)} unique artists:")
    
    # Save to file
    output_file = "all_artists.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for artist in artists:
            f.write(f"{artist}\n")
    
    # Display first 50 artists
    print("\nFirst 50 artists:")
    for i, artist in enumerate(artists[:50], 1):
        print(f"{i:3d}. {artist}")
    
    if len(artists) > 50:
        print(f"\n... and {len(artists) - 50} more artists")
        print(f"Full list saved to: {output_file}")
    
    # Show some statistics
    print(f"\nTotal unique artists: {len(artists)}")
    print(f"Artists starting with A-Z: {len([a for a in artists if a[0].isalpha()])}")
    print(f"Artists starting with numbers/symbols: {len([a for a in artists if not a[0].isalpha()])}")

if __name__ == "__main__":
    main()
