import os
import re

AUDIO_EXTS = {".mp3", ".opus", ".flac", ".m4a", ".wav", ".ogg", ".aac"}

# Separators used between multiple artists in filenames / song lists
ARTIST_SEP = re.compile(r"\s*(?:,|&|feat\.?|ft\.?|\bx\b|/)\s*", re.IGNORECASE)


def normalize(text):
    """Lowercase, collapse punctuation/spaces for fuzzy comparison."""
    text = text.lower()
    text = re.sub(r"['\"\-–—_.,!?()&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_artists(artist_str):
    """'Lady Gaga, Bruno Mars' -> ['lady gaga', 'bruno mars']"""
    parts = ARTIST_SEP.split(artist_str)
    return [normalize(p) for p in parts if p.strip()]


def parse_song(song):
    """'Artist - Title' -> ([normalized_artists], normalized_title)"""
    if " - " in song:
        artist_str, title = song.split(" - ", 1)
        return split_artists(artist_str), normalize(title)
    return [], normalize(song)


def build_local_index(folder):
    """
    Scan an audio folder and return (flat, entries):
      flat    - set of full normalized stems, for fast exact-match
      entries - list of (set_of_artist_tokens, normalized_title)
    """
    entries = []
    flat = set()
    for fname in os.listdir(folder):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in AUDIO_EXTS:
            continue
        flat.add(normalize(stem))
        artists, title = parse_song(stem)
        entries.append((set(artists), title))
    return flat, entries


def already_exists(song, flat_index, entries):
    """
    True if 'song' (e.g. 'Artist - Title') already exists in the local library.

    Matching priority:
      1. Exact full normalized match (fast path)
      2. Title matches AND at least one artist token overlaps
      3. Title-only match as fallback (title must be longer than 4 chars)
    """
    norm_song = normalize(song)
    if norm_song in flat_index:
        return True

    query_artists, query_title = parse_song(song)
    query_artists = set(query_artists)
    if not query_title or len(query_title) <= 4:
        return False

    for lib_artists, lib_title in entries:
        if lib_title != query_title:
            continue
        if not query_artists or not lib_artists:
            return True
        if query_artists & lib_artists:
            return True

    return False
