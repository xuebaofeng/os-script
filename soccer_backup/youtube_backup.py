import os
import re
import sys
import json
import time
import hashlib
import sqlite3
from datetime import datetime, timezone

import requests

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# ============================================================
# Configuration
# ============================================================

DB_FILE = "soccer_backup.db"
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

CHUNK_SIZE = 8 * 1024 * 1024

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)

YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={}"

VIDEO_EXTENSIONS = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
}


# ============================================================
# SQLite
# ============================================================

def db_connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn):
    """
    Upgrade existing videos table without deleting data.
    """

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(videos)")
    }

    required = {
        "upload_session_url": "TEXT",
        "uploaded_bytes": "INTEGER DEFAULT 0",
        "error_message": "TEXT",
        "last_attempt_at": "TEXT",
    }

    for name, definition in required.items():
        if name not in columns:
            print(f"Adding DB column: {name}")
            conn.execute(
                f"ALTER TABLE videos ADD COLUMN {name} {definition}"
            )

    conn.commit()


def find_video(conn, filepath):
    """
    Prefer exact original_path.
    Fallback to unique filename.
    """

    row = conn.execute(
        """
        SELECT *
        FROM videos
        WHERE original_path = ?
            LIMIT 1
        """,
        (filepath,),
    ).fetchone()

    if row:
        return row

    filename = os.path.basename(filepath)

    rows = conn.execute(
        """
        SELECT *
        FROM videos
        WHERE original_filename = ?
        """,
        (filename,),
    ).fetchall()

    if len(rows) == 1:
        return rows[0]

    return None


def update_video(conn, video_id, **fields):
    if not fields:
        return

    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    assignments = ", ".join(
        f"{key} = ?" for key in fields
    )

    values = list(fields.values())
    values.append(video_id)

    conn.execute(
        f"""
        UPDATE videos
        SET {assignments}
        WHERE id = ?
        """,
        values,
    )

    conn.commit()


# ============================================================
# SHA256
# ============================================================

def sha256_file(filepath):
    print("Calculating SHA256...")

    h = hashlib.sha256()

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(16 * 1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    result = h.hexdigest()

    print(f"SHA256: {result}")

    return result


# ============================================================
# Trace metadata
# ============================================================

def load_match(conn, game_id):
    row = conn.execute(
        """
        SELECT *
        FROM matches
        WHERE game_id = ?
        """,
        (game_id,),
    ).fetchone()

    return row


def build_title(match, period):
    home = match["home_team_title"] or match["home_team_name"] or ""
    away = match["away_team_title"] or match["away_team_name"] or ""

    home_abbr = match["home_team_abbr"] or ""
    away_abbr = match["away_team_abbr"] or ""

    if home_abbr:
        home = f"{home} ({home_abbr})"

    if away_abbr:
        away = f"{away} ({away_abbr})"

    match_date = match["match_date"] or ""

    home_score = match["home_score"]
    away_score = match["away_score"]

    score = ""

    if home_score is not None and away_score is not None:
        score = f" | {home_score}-{away_score}"

    return (
        f"{home} | vs | {away}"
        f" | {match_date}"
        f"{score}"
        f" | {period}"
    )


def build_backup_block(
        match,
        game_id,
        period,
        filename,
        sha256,
):
    home = match["home_team_title"] or match["home_team_name"] or ""
    away = match["away_team_title"] or match["away_team_name"] or ""

    return f"""[SOCCER_BACKUP]
game_id={game_id}
period={period}
sha256={sha256}
original_filename={filename}
match_date={match["match_date"] or ""}
home_team={home}
away_team={away}
home_score={match["home_score"] if match["home_score"] is not None else ""}
away_score={match["away_score"] if match["away_score"] is not None else ""}
competition={match["division_title"] or ""}
source=Trace
[/SOCCER_BACKUP]"""


def build_description(
        match,
        game_id,
        period,
        filename,
        sha256,
):
    home = match["home_team_title"] or match["home_team_name"] or ""
    away = match["away_team_title"] or match["away_team_name"] or ""

    home_score = match["home_score"]
    away_score = match["away_score"]

    score = ""

    if home_score is not None and away_score is not None:
        score = f"{home_score}-{away_score}"

    block = build_backup_block(
        match,
        game_id,
        period,
        filename,
        sha256,
    )

    return f"""Youth soccer match video backup.

Match Date: {match["match_date"] or ""}
Home: {home}
Away: {away}
Score: {score}
Period: {period}
Competition: {match["division_title"] or ""}
Trace Game ID: {game_id}

Original Filename: {filename}
SHA256: {sha256}

Source: Trace

{block}
"""


def build_tags(match, game_id, period):
    tags = [
        "soccer",
        "youth soccer",
        "MLS NEXT",
        "MLS Next U15",
        "U15",
        period,
        str(game_id),
    ]

    for key in [
        "home_team_title",
        "home_team_abbr",
        "away_team_title",
        "away_team_abbr",
        "division_title",
        "match_date",
    ]:
        value = match[key]

        if value:
            tags.append(str(value))

    # YouTube tag limit is 500 characters.
    result = []

    total = 0

    for tag in tags:
        if tag in result:
            continue

        add = len(tag) + (1 if result else 0)

        if total + add > 500:
            break

        result.append(tag)
        total += add

    return result


# ============================================================
# OAuth
# ============================================================

def get_credentials():
    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES,
            )
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            print("Refreshing Google OAuth token...")
            creds.refresh(Request())

        else:
            print("Starting Google OAuth...")

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent",
            )

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


# ============================================================
# YouTube API
# ============================================================

def youtube_session():
    creds = get_credentials()

    return AuthorizedSession(creds)


def youtube_video_info(session, video_id):
    """
    Directly verify a known YouTube video ID.
    """

    response = session.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet,status,processingDetails,contentDetails",
            "id": video_id,
        },
        timeout=60,
    )

    if response.status_code != 200:
        return None

    data = response.json()

    items = data.get("items", [])

    if not items:
        return None

    return items[0]


def extract_backup_metadata(description):
    """
    Extract our machine-readable metadata block.
    """

    if not description:
        return {}

    match = re.search(
        r"\[SOCCER_BACKUP\](.*?)\[/SOCCER_BACKUP\]",
        description,
        re.DOTALL,
    )

    if not match:
        return {}

    result = {}

    for line in match.group(1).splitlines():
        line = line.strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        result[key.strip()] = value.strip()

    return result


def get_uploads_playlist_id(session):
    response = session.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "part": "contentDetails",
            "mine": "true",
        },
        timeout=60,
    )

    response.raise_for_status()

    items = response.json().get("items", [])

    if not items:
        raise RuntimeError("No YouTube channel found.")

    return (
        items[0]["contentDetails"]
        ["relatedPlaylists"]
        ["uploads"]
    )


def find_existing_video_on_youtube(
        session,
        sha256,
        game_id,
        period,
):
    """
    Scan the user's own YouTube uploads and find our backup record.

    Priority:
      1. SHA256 exact match
      2. Game ID + Period exact match
    """

    print()
    print("Checking YouTube for an existing upload...")

    playlist_id = get_uploads_playlist_id(session)

    page_token = None

    sha_match = None
    game_period_match = None

    scanned = 0

    while True:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }

        if page_token:
            params["pageToken"] = page_token

        response = session.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params=params,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        ids = []

        for item in data.get("items", []):
            video_id = (
                item.get("contentDetails", {})
                .get("videoId")
            )

            if video_id:
                ids.append(video_id)

        if ids:
            response = session.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,status,processingDetails",
                    "id": ",".join(ids),
                },
                timeout=60,
            )

            response.raise_for_status()

            videos = response.json().get("items", [])

            scanned += len(videos)

            for video in videos:
                video_id = video["id"]

                snippet = video.get("snippet", {})
                description = snippet.get("description", "")

                metadata = extract_backup_metadata(description)

                if metadata.get("sha256") == sha256:
                    sha_match = video
                    break

                if (
                        metadata.get("game_id") == str(game_id)
                        and metadata.get("period") == period
                ):
                    game_period_match = video

        if sha_match:
            break

        page_token = data.get("nextPageToken")

        if not page_token:
            break

    print(f"Checked {scanned} YouTube videos.")

    if sha_match:
        print("FOUND EXACT SHA256 MATCH.")
        return sha_match, "sha256"

    if game_period_match:
        print("FOUND GAME ID + PERIOD MATCH.")
        return game_period_match, "game_period"

    print("No existing backup video found.")

    return None, None


# ============================================================
# Reconcile SQLite
# ============================================================

def reconcile_existing_video(
        conn,
        video_row,
        youtube_video,
        match_type,
):
    video_id = youtube_video["id"]

    status = (
        youtube_video
        .get("status", {})
        .get("uploadStatus", "uploaded")
    )

    processing_status = (
        youtube_video
        .get("processingDetails", {})
        .get("processingStatus")
    )

    if processing_status == "succeeded":
        youtube_status = "completed"

    elif status in ("deleted", "failed"):
        youtube_status = status

    else:
        youtube_status = "uploaded"

    update_video(
        conn,
        video_row["id"],
        youtube_id=video_id,
        youtube_status=youtube_status,
        upload_session_url=None,
        uploaded_bytes=0,
        error_message=None,
    )

    print()
    print("========================================")
    print("EXISTING YOUTUBE VIDEO FOUND")
    print("========================================")
    print(f"YouTube ID : {video_id}")
    print(f"URL        : {YOUTUBE_WATCH_URL.format(video_id)}")
    print(f"Match type : {match_type}")
    print(f"Status     : {youtube_status}")
    print("SQLite     : updated")
    print("Upload     : SKIPPED")
    print("========================================")

    return True


# ============================================================
# Upload session
# ============================================================

def create_upload_session(
        session,
        metadata,
        content_type,
        file_size,
):
    headers = {
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": content_type,
        "Content-Type": "application/json; charset=UTF-8",
    }

    body = {
        "snippet": metadata["snippet"],
        "status": metadata["status"],
    }

    response = session.post(
        UPLOAD_URL,
        headers=headers,
        json=body,
        timeout=60,
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Could not create upload session: "
            f"{response.status_code} {response.text}"
        )

    location = response.headers.get("Location")

    if not location:
        raise RuntimeError(
            "YouTube did not return an upload session URL."
        )

    return location


def query_upload_position(
        session,
        session_url,
        file_size,
):
    headers = {
        "Content-Length": "0",
        "Content-Range": f"bytes */{file_size}",
    }

    response = session.put(
        session_url,
        headers=headers,
        timeout=60,
    )

    if response.status_code == 308:
        range_header = response.headers.get("Range")

        if not range_header:
            return 0

        match = re.search(
            r"bytes=0-(\d+)",
            range_header,
        )

        if not match:
            return 0

        return int(match.group(1)) + 1

    if response.status_code in (200, 201):
        return file_size

    if response.status_code in (404, 410):
        raise RuntimeError("UPLOAD_SESSION_EXPIRED")

    if response.status_code == 401:
        raise RuntimeError("AUTH_REFRESH_REQUIRED")

    raise RuntimeError(
        f"Upload position query failed: "
        f"{response.status_code} {response.text}"
    )


def upload_chunks(
        session,
        session_url,
        filepath,
        start_byte,
        video_row,
        conn,
):
    file_size = os.path.getsize(filepath)

    content_type = VIDEO_EXTENSIONS.get(
        os.path.splitext(filepath)[1].lower(),
        "application/octet-stream",
    )

    current = start_byte

    with open(filepath, "rb") as f:

        f.seek(current)

        while current < file_size:
            data = f.read(CHUNK_SIZE)

            if not data:
                break

            end = current + len(data) - 1

            headers = {
                "Content-Length": str(len(data)),
                "Content-Type": content_type,
                "Content-Range": (
                    f"bytes {current}-{end}/{file_size}"
                ),
            }

            while True:
                try:
                    response = session.put(
                        session_url,
                        headers=headers,
                        data=data,
                        timeout=300,
                    )

                except requests.RequestException as e:
                    print()
                    print(f"Network error: {e}")
                    print("Progress preserved in SQLite.")
                    raise

                if response.status_code in (200, 201):
                    result = response.json()

                    update_video(
                        conn,
                        video_row["id"],
                        youtube_id=result["id"],
                        youtube_status="completed",
                        upload_session_url=None,
                        uploaded_bytes=0,
                        error_message=None,
                    )

                    print()
                    print("========================================")
                    print("UPLOAD COMPLETED")
                    print("========================================")
                    print(
                        f"YouTube ID : {result['id']}"
                    )
                    print(
                        "URL        : "
                        + YOUTUBE_WATCH_URL.format(result["id"])
                    )
                    print("========================================")

                    return result["id"]

                if response.status_code == 308:
                    current = end + 1

                    update_video(
                        conn,
                        video_row["id"],
                        uploaded_bytes=current,
                        youtube_status="uploading",
                        upload_session_url=session_url,
                        error_message=None,
                    )

                    percent = (
                        current * 100 / file_size
                        if file_size
                        else 100
                    )

                    print(
                        f"\rUploaded "
                        f"{current:,}/{file_size:,} "
                        f"({percent:.1f}%)",
                        end="",
                        flush=True,
                    )

                    break

                if response.status_code in (404, 410):
                    raise RuntimeError(
                        "UPLOAD_SESSION_EXPIRED"
                    )

                if response.status_code == 401:
                    raise RuntimeError(
                        "AUTH_REFRESH_REQUIRED"
                    )

                if response.status_code in (
                        408,
                        429,
                        500,
                        502,
                        503,
                        504,
                ):
                    print()
                    print(
                        f"Temporary YouTube error "
                        f"{response.status_code}; retrying..."
                    )

                    time.sleep(5)

                    continue

                raise RuntimeError(
                    f"Chunk upload failed: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

    raise RuntimeError(
        "Upload ended without YouTube completion."
    )


# ============================================================
# Main upload
# ============================================================

def upload_video(filepath):
    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        raise FileNotFoundError(filepath)

    extension = os.path.splitext(filepath)[1].lower()

    if extension not in VIDEO_EXTENSIONS:
        raise RuntimeError(
            f"Unsupported video extension: {extension}"
        )

    filename = os.path.basename(filepath)

    conn = db_connect()

    ensure_schema(conn)

    video_row = find_video(conn, filepath)

    if not video_row:
        raise RuntimeError(
            "Video is not registered in SQLite.\n\n"
            "Run trace_import.py first:\n"
            f'py trace_import.py "{filepath}" GAME_ID '
            '--trace-json=trace.json'
        )

    game_id = video_row["game_id"]
    period = video_row["period"]

    if not period:
        raise RuntimeError(
            "Video has no period. Expected period-1 or period-2."
        )

    match = load_match(conn, game_id)

    if not match:
        raise RuntimeError(
            f"No match metadata found for Game ID {game_id}."
        )

    # --------------------------------------------------------
    # SHA256
    # --------------------------------------------------------

    sha256 = video_row["sha256"]

    if not sha256:
        sha256 = sha256_file(filepath)

        update_video(
            conn,
            video_row["id"],
            sha256=sha256,
        )

    else:
        print(f"SHA256 from SQLite: {sha256}")

    # --------------------------------------------------------
    # OAuth / YouTube
    # --------------------------------------------------------

    session = youtube_session()

    # --------------------------------------------------------
    # FIRST CHECK:
    # If SQLite has a YouTube ID, verify it directly.
    # --------------------------------------------------------

    if video_row["youtube_id"]:
        print()
        print(
            "SQLite contains YouTube ID: "
            + video_row["youtube_id"]
        )

        existing = youtube_video_info(
            session,
            video_row["youtube_id"],
        )

        if existing:
            reconcile_existing_video(
                conn,
                video_row,
                existing,
                "sqlite_youtube_id",
            )

            conn.close()
            return

        print(
            "SQLite YouTube ID no longer exists. "
            "Searching uploads..."
        )

    # --------------------------------------------------------
    # SECOND CHECK:
    # Search own YouTube uploads using SHA256.
    # --------------------------------------------------------

    existing, match_type = find_existing_video_on_youtube(
        session,
        sha256,
        game_id,
        period,
    )

    if existing:
        reconcile_existing_video(
            conn,
            video_row,
            existing,
            match_type,
        )

        conn.close()
        return

    # --------------------------------------------------------
    # Build metadata
    # --------------------------------------------------------

    title = build_title(
        match,
        period,
    )

    description = build_description(
        match,
        game_id,
        period,
        filename,
        sha256,
    )

    tags = build_tags(
        match,
        game_id,
        period,
    )

    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "17",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }

    print()
    print("========================================")
    print("NEW YOUTUBE UPLOAD")
    print("========================================")
    print(f"File       : {filename}")
    print(f"Game ID    : {game_id}")
    print(f"Period     : {period}")
    print(f"Match Date : {match['match_date']}")
    print(f"Title      : {title}")
    print(f"Size       : {os.path.getsize(filepath):,} bytes")
    print("Privacy    : private")
    print("========================================")

    # --------------------------------------------------------
    # Existing resumable session
    # --------------------------------------------------------

    session_url = video_row["upload_session_url"]
    uploaded_bytes = video_row["uploaded_bytes"] or 0

    file_size = os.path.getsize(filepath)

    if session_url:
        print()
        print("Existing resumable upload session found.")

        try:
            server_position = query_upload_position(
                session,
                session_url,
                file_size,
            )

            print(
                f"YouTube upload position: "
                f"{server_position:,}/{file_size:,}"
            )

            uploaded_bytes = server_position

        except RuntimeError as e:
            if str(e) == "UPLOAD_SESSION_EXPIRED":
                print(
                    "Existing upload session expired. "
                    "Creating a new one."
                )

                session_url = None
                uploaded_bytes = 0

            else:
                raise

    # --------------------------------------------------------
    # Create new resumable session
    # --------------------------------------------------------

    if not session_url:

        content_type = VIDEO_EXTENSIONS[extension]

        print("Creating YouTube resumable upload session...")

        session_url = create_upload_session(
            session,
            metadata,
            content_type,
            file_size,
        )

        uploaded_bytes = 0

        update_video(
            conn,
            video_row["id"],
            upload_session_url=session_url,
            uploaded_bytes=0,
            youtube_status="uploading",
            error_message=None,
            last_attempt_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    try:
        youtube_id = upload_chunks(
            session,
            session_url,
            filepath,
            uploaded_bytes,
            video_row,
            conn,
        )

    except KeyboardInterrupt:
        print()
        print("Upload interrupted by user.")
        print("Resumable session preserved.")

        update_video(
            conn,
            video_row["id"],
            upload_session_url=session_url,
            uploaded_bytes=uploaded_bytes,
            youtube_status="paused",
            error_message=None,
        )

        conn.close()
        return

    except Exception as e:
        print()
        print(f"ERROR: {e}")

        update_video(
            conn,
            video_row["id"],
            upload_session_url=session_url,
            uploaded_bytes=uploaded_bytes,
            youtube_status="paused",
            error_message=str(e),
        )

        conn.close()
        raise

    conn.close()

    return youtube_id


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            'Usage:\n'
            '  py youtube_backup.py "VIDEO_FILE"'
        )
        sys.exit(1)

    try:
        upload_video(sys.argv[1])

    except Exception as e:
        print()
        print(f"ERROR: {e}")
        sys.exit(1)