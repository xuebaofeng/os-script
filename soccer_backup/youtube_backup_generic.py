import argparse
import hashlib
import os
import sqlite3
import sys
from datetime import datetime, timezone

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# ============================================================
# Configuration
# ============================================================

DB_FILE = "soccer_backup.db"

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

# Needed for upload + playlist management
SCOPES = [
    "https://www.googleapis.com/auth/youtube"
]

UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable"
    "&part=snippet,status"
)

PLAYLIST_ITEMS_URL = (
    "https://www.googleapis.com/youtube/v3/playlistItems"
)

CHUNK_SIZE = 8 * 1024 * 1024

VIDEO_EXTENSIONS = {
    ".mov",
    ".mp4",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
}


# ============================================================
# Exceptions
# ============================================================

class YouTubeUploadLimitExceeded(Exception):
    pass


# ============================================================
# Time
# ============================================================

def now_utc():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Database
# ============================================================

def init_db(conn):
    conn.execute("""
                 CREATE TABLE IF NOT EXISTS generic_videos (
                                                               id INTEGER PRIMARY KEY AUTOINCREMENT,

                                                               original_filename TEXT NOT NULL,
                                                               original_path TEXT NOT NULL,

                                                               file_size INTEGER,
                                                               sha256 TEXT UNIQUE,

                                                               youtube_id TEXT,
                                                               youtube_status TEXT DEFAULT 'pending',

                                                               playlist_id TEXT,
                                                               playlist_status TEXT DEFAULT 'pending',
                                                               playlist_item_id TEXT,

                                                               upload_session_url TEXT,
                                                               uploaded_bytes INTEGER DEFAULT 0,

                                                               error_message TEXT,
                                                               last_attempt_at TEXT,

                                                               created_at TEXT NOT NULL,
                                                               updated_at TEXT NOT NULL
                 )
                 """)

    # --------------------------------------------------------
    # Upgrade older database versions
    # --------------------------------------------------------

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(generic_videos)"
        ).fetchall()
    }

    if "playlist_id" not in columns:
        conn.execute("""
                     ALTER TABLE generic_videos
                         ADD COLUMN playlist_id TEXT
                     """)

    if "playlist_status" not in columns:
        conn.execute("""
                     ALTER TABLE generic_videos
                         ADD COLUMN playlist_status TEXT DEFAULT 'pending'
                     """)

    if "playlist_item_id" not in columns:
        conn.execute("""
                     ALTER TABLE generic_videos
                         ADD COLUMN playlist_item_id TEXT
                     """)

    conn.commit()


# ============================================================
# SHA256
# ============================================================

def calculate_sha256(path):
    print(f"SHA256: {path}")

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# File discovery
# ============================================================

def find_video_files(folder):
    files = []

    for root, dirs, filenames in os.walk(folder):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()

            if ext in VIDEO_EXTENSIONS:
                files.append(
                    os.path.join(root, filename)
                )

    files.sort()

    return files


# ============================================================
# Database lookup
# ============================================================

def get_by_sha256(conn, sha256):
    return conn.execute("""
                        SELECT *
                        FROM generic_videos
                        WHERE sha256 = ?
                        """, (sha256,)).fetchone()


# ============================================================
# Insert / get video
# ============================================================

def insert_or_get_file(
        conn,
        path,
        sha256,
        file_size
):
    filename = os.path.basename(path)
    timestamp = now_utc()

    row = get_by_sha256(
        conn,
        sha256
    )

    if row:
        return row

    conn.execute("""
                 INSERT INTO generic_videos (
                     original_filename,
                     original_path,
                     file_size,
                     sha256,
                     youtube_status,
                     playlist_status,
                     created_at,
                     updated_at
                 )
                 VALUES (
                            ?, ?, ?, ?,
                            'pending',
                            'pending',
                            ?, ?
                        )
                 """, (
                     filename,
                     path,
                     file_size,
                     sha256,
                     timestamp,
                     timestamp
                 ))

    conn.commit()

    return get_by_sha256(
        conn,
        sha256
    )


# ============================================================
# OAuth
# ============================================================

def save_credentials(creds):
    with open(
            TOKEN_FILE,
            "w",
            encoding="utf-8"
    ) as token:
        token.write(
            creds.to_json()
        )


def get_credentials():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # --------------------------------------------------------
    # Refresh existing token
    # --------------------------------------------------------

    if (
            creds
            and creds.expired
            and creds.refresh_token
    ):
        print(
            "Refreshing YouTube credentials..."
        )

        creds.refresh(
            Request()
        )

        save_credentials(
            creds
        )

    # --------------------------------------------------------
    # New authorization
    # --------------------------------------------------------

    if not creds or not creds.valid:
        print()
        print(
            "YouTube authorization required."
        )
        print()

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        save_credentials(
            creds
        )

    return creds


def ensure_credentials(creds):
    if creds.valid:
        return

    if (
            creds.expired
            and creds.refresh_token
    ):
        print(
            "Refreshing YouTube access token..."
        )

        creds.refresh(
            Request()
        )

        save_credentials(
            creds
        )

        return

    raise RuntimeError(
        "YouTube credentials are invalid "
        "and cannot be refreshed."
    )


# ============================================================
# YouTube metadata
# ============================================================

def build_title(filename):
    return filename


def build_description(
        original_path,
        sha256
):
    return (
        "Video Backup\n"
        "\n"
        f"Original Path: {original_path}\n"
        f"SHA256: {sha256}\n"
    )


# ============================================================
# Create resumable upload session
# ============================================================

def create_upload_session(
        creds,
        filename,
        original_path,
        sha256,
        file_size
):
    ensure_credentials(
        creds
    )

    body = {
        "snippet": {
            "title": build_title(
                filename
            ),
            "description": build_description(
                original_path,
                sha256
            ),
            "categoryId": "17",
        },
        "status": {
            "privacyStatus": "private"
        }
    }

    headers = {
        "Authorization": (
            f"Bearer {creds.token}"
        ),
        "Content-Type": (
            "application/json"
        ),
        "X-Upload-Content-Length": (
            str(file_size)
        ),
        "X-Upload-Content-Type": (
            "video/*"
        ),
    }

    response = requests.post(
        UPLOAD_URL,
        headers=headers,
        json=body,
        timeout=60
    )

    # --------------------------------------------------------
    # Retry once after token refresh
    # --------------------------------------------------------

    if response.status_code == 401:
        print(
            "Upload session returned 401."
        )

        if creds.refresh_token:
            creds.refresh(
                Request()
            )

            save_credentials(
                creds
            )

            headers["Authorization"] = (
                f"Bearer {creds.token}"
            )

            response = requests.post(
                UPLOAD_URL,
                headers=headers,
                json=body,
                timeout=60
            )

    if response.status_code not in (
            200,
            201
    ):
        try:
            error_data = response.json()
        except Exception:
            error_data = {}

        reason = ""

        errors = (
            error_data
            .get("error", {})
            .get("errors", [])
        )

        if errors:
            reason = errors[0].get(
                "reason",
                ""
            )

        if reason == "uploadLimitExceeded":
            raise YouTubeUploadLimitExceeded(
                "YouTube upload limit exceeded."
            )

        raise RuntimeError(
            "Create upload session failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    session_url = response.headers.get(
        "Location"
    )

    if not session_url:
        raise RuntimeError(
            "YouTube did not return "
            "a resumable upload URL."
        )

    return session_url


# ============================================================
# Upload one file
# ============================================================

def upload_file(
        conn,
        row,
        creds
):
    path = row["original_path"]
    filename = row["original_filename"]
    sha256 = row["sha256"]
    file_size = row["file_size"]

    session_url = (
        row["upload_session_url"]
    )

    uploaded_bytes = (
            row["uploaded_bytes"]
            or 0
    )

    # --------------------------------------------------------
    # Create upload session
    # --------------------------------------------------------

    if not session_url:
        print()
        print(
            "Creating YouTube "
            "resumable upload session..."
        )

        session_url = create_upload_session(
            creds,
            filename,
            path,
            sha256,
            file_size
        )

        timestamp = now_utc()

        conn.execute("""
                     UPDATE generic_videos
                     SET
                         upload_session_url = ?,
                         uploaded_bytes = 0,
                         last_attempt_at = ?,
                         updated_at = ?
                     WHERE id = ?
                     """, (
                         session_url,
                         timestamp,
                         timestamp,
                         row["id"]
                     ))

        conn.commit()

        uploaded_bytes = 0

    # --------------------------------------------------------
    # Upload chunks
    # --------------------------------------------------------

    print()
    print(
        f"Uploading: {filename}"
    )
    print(
        f"Size: {file_size:,} bytes"
    )
    print(
        f"Already uploaded: "
        f"{uploaded_bytes:,} bytes"
    )
    print()

    with open(
            path,
            "rb"
    ) as f:

        if uploaded_bytes:
            f.seek(
                uploaded_bytes
            )

        while uploaded_bytes < file_size:

            chunk = f.read(
                CHUNK_SIZE
            )

            if not chunk:
                break

            chunk_start = uploaded_bytes

            chunk_end = (
                    uploaded_bytes
                    + len(chunk)
                    - 1
            )

            headers = {
                "Content-Length": (
                    str(len(chunk))
                ),
                "Content-Range": (
                    f"bytes "
                    f"{chunk_start}-"
                    f"{chunk_end}/"
                    f"{file_size}"
                ),
            }

            response = requests.put(
                session_url,
                headers=headers,
                data=chunk,
                timeout=300
            )

            # ------------------------------------------------
            # Upload complete
            # ------------------------------------------------

            if response.status_code in (
                    200,
                    201
            ):
                data = response.json()

                youtube_id = data["id"]

                timestamp = now_utc()

                conn.execute("""
                             UPDATE generic_videos
                             SET
                                 youtube_id = ?,
                                 youtube_status = 'completed',
                                 upload_session_url = NULL,
                                 uploaded_bytes = ?,
                                 error_message = NULL,
                                 updated_at = ?
                             WHERE id = ?
                             """, (
                                 youtube_id,
                                 file_size,
                                 timestamp,
                                 row["id"]
                             ))

                conn.commit()

                print()
                print(
                    "UPLOAD COMPLETE"
                )
                print(
                    f"YouTube ID: {youtube_id}"
                )
                print()

                return youtube_id

            # ------------------------------------------------
            # Chunk accepted, continue
            # ------------------------------------------------

            if response.status_code == 308:

                range_header = (
                    response.headers.get(
                        "Range"
                    )
                )

                if range_header:
                    last_byte = int(
                        range_header
                        .split("-")[-1]
                    )

                    uploaded_bytes = (
                            last_byte + 1
                    )
                else:
                    uploaded_bytes = (
                            chunk_end + 1
                    )

                timestamp = now_utc()

                conn.execute("""
                             UPDATE generic_videos
                             SET
                                 uploaded_bytes = ?,
                                 last_attempt_at = ?,
                                 updated_at = ?
                             WHERE id = ?
                             """, (
                                 uploaded_bytes,
                                 timestamp,
                                 timestamp,
                                 row["id"]
                             ))

                conn.commit()

                percent = (
                        uploaded_bytes
                        * 100
                        / file_size
                )

                print(
                    f"\rProgress: "
                    f"{uploaded_bytes:,} / "
                    f"{file_size:,} "
                    f"({percent:.1f}%)",
                    end="",
                    flush=True
                )

                continue

            # ------------------------------------------------
            # Session expired
            # ------------------------------------------------

            if response.status_code in (
                    404,
                    410
            ):
                timestamp = now_utc()

                conn.execute("""
                             UPDATE generic_videos
                             SET
                                 upload_session_url = NULL,
                                 uploaded_bytes = 0,
                                 updated_at = ?
                             WHERE id = ?
                             """, (
                                 timestamp,
                                 row["id"]
                             ))

                conn.commit()

                raise RuntimeError(
                    "YouTube upload session "
                    "expired or is no longer valid."
                )

            # ------------------------------------------------
            # Authentication error
            # ------------------------------------------------

            if response.status_code == 401:
                raise RuntimeError(
                    "YouTube returned 401 "
                    "during resumable upload."
                )

            # ------------------------------------------------
            # Other error
            # ------------------------------------------------

            raise RuntimeError(
                "YouTube upload failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

    raise RuntimeError(
        "Upload ended before YouTube "
        "returned a completed video ID."
    )


# ============================================================
# Add video to playlist
# ============================================================

def add_to_playlist(
        creds,
        playlist_id,
        youtube_id
):
    ensure_credentials(
        creds
    )

    headers = {
        "Authorization": (
            f"Bearer {creds.token}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }

    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": youtube_id,
            },
        }
    }

    response = requests.post(
        PLAYLIST_ITEMS_URL,
        params={
            "part": "snippet"
        },
        headers=headers,
        json=body,
        timeout=60
    )

    # --------------------------------------------------------
    # Retry once after token refresh
    # --------------------------------------------------------

    if response.status_code == 401:

        print(
            "Playlist request returned 401. "
            "Refreshing token..."
        )

        if creds.refresh_token:

            creds.refresh(
                Request()
            )

            save_credentials(
                creds
            )

            headers["Authorization"] = (
                f"Bearer {creds.token}"
            )

            response = requests.post(
                PLAYLIST_ITEMS_URL,
                params={
                    "part": "snippet"
                },
                headers=headers,
                json=body,
                timeout=60
            )

    if response.status_code not in (
            200,
            201
    ):
        raise RuntimeError(
            "Add to playlist failed: "
            f"{response.status_code} "
            f"{response.text}"
        )

    data = response.json()

    return data["id"]


# ============================================================
# Get all playlist items
# ============================================================

def get_all_playlist_items(
        creds,
        playlist_id
):
    ensure_credentials(
        creds
    )

    items = []
    page_token = None

    while True:

        headers = {
            "Authorization": (
                f"Bearer {creds.token}"
            )
        }

        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }

        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            PLAYLIST_ITEMS_URL,
            headers=headers,
            params=params,
            timeout=60
        )

        # ----------------------------------------------------
        # Retry once after token refresh
        # ----------------------------------------------------

        if response.status_code == 401:

            print(
                "Playlist list request returned 401. "
                "Refreshing token..."
            )

            if creds.refresh_token:

                creds.refresh(
                    Request()
                )

                save_credentials(
                    creds
                )

                headers["Authorization"] = (
                    f"Bearer {creds.token}"
                )

                response = requests.get(
                    PLAYLIST_ITEMS_URL,
                    headers=headers,
                    params=params,
                    timeout=60
                )

        if response.status_code != 200:

            raise RuntimeError(
                "Get playlist items failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

        data = response.json()

        for item in data.get("items", []):

            video_id = (
                item
                .get("contentDetails", {})
                .get("videoId")
            )

            if not video_id:
                continue

            items.append({
                "playlist_item_id": item["id"],
                "video_id": video_id,
                "title": (
                    item
                    .get("snippet", {})
                    .get("title", "")
                ),
                "position": (
                    item
                    .get("snippet", {})
                    .get("position")
                ),
            })

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return items


# ============================================================
# Delete playlist item
# ============================================================

def delete_playlist_item(
        creds,
        playlist_item_id
):
    ensure_credentials(
        creds
    )

    headers = {
        "Authorization": (
            f"Bearer {creds.token}"
        )
    }

    response = requests.delete(
        PLAYLIST_ITEMS_URL,
        params={
            "id": playlist_item_id
        },
        headers=headers,
        timeout=60
    )

    # --------------------------------------------------------
    # Retry once after token refresh
    # --------------------------------------------------------

    if response.status_code == 401:

        print(
            "Playlist delete request returned 401. "
            "Refreshing token..."
        )

        if creds.refresh_token:

            creds.refresh(
                Request()
            )

            save_credentials(
                creds
            )

            headers["Authorization"] = (
                f"Bearer {creds.token}"
            )

            response = requests.delete(
                PLAYLIST_ITEMS_URL,
                params={
                    "id": playlist_item_id
                },
                headers=headers,
                timeout=60
            )

    if response.status_code != 204:

        raise RuntimeError(
            "Delete playlist item failed: "
            f"{response.status_code} "
            f"{response.text}"
        )


# ============================================================
# Dedupe playlist
# ============================================================

def command_dedupe(
        playlist_id,
        dry_run=False
):
    print()
    print(
        f"Playlist: {playlist_id}"
    )

    if dry_run:
        print(
            "Mode: DRY RUN "
            "(nothing will be deleted)"
        )
    else:
        print(
            "Mode: DELETE DUPLICATES"
        )

    print()

    creds = get_credentials()

    print(
        "Reading playlist..."
    )

    items = get_all_playlist_items(
        creds,
        playlist_id
    )

    print()
    print(
        f"Total playlist items: {len(items)}"
    )

    if not items:
        print(
            "Playlist is empty."
        )

        return

    # --------------------------------------------------------
    # Find duplicates
    #
    # Keep the first occurrence.
    # Delete every later occurrence.
    # --------------------------------------------------------

    seen = set()
    duplicates = []

    for item in items:

        video_id = item["video_id"]

        if video_id in seen:

            duplicates.append(
                item
            )

        else:

            seen.add(
                video_id
            )

    print(
        f"Unique videos:        {len(seen)}"
    )

    print(
        f"Duplicate items:      {len(duplicates)}"
    )

    print()

    if not duplicates:

        print(
            "No duplicates found."
        )

        return

    # --------------------------------------------------------
    # Display duplicates
    # --------------------------------------------------------

    print(
        "Duplicates:"
    )

    print()

    for item in duplicates:

        print(
            f"  DELETE"
            f"  Video ID: {item['video_id']}"
        )

        print(
            f"          Title: "
            f"{item['title']}"
        )

        print(
            f"          Playlist item ID: "
            f"{item['playlist_item_id']}"
        )

    print()

    # --------------------------------------------------------
    # Dry run
    # --------------------------------------------------------

    if dry_run:

        print(
            "DRY RUN COMPLETE"
        )

        print(
            f"Would delete: "
            f"{len(duplicates)} playlist item(s)."
        )

        return

    # --------------------------------------------------------
    # Delete duplicates
    # --------------------------------------------------------

    deleted = 0
    errors = 0

    print(
        "Deleting duplicates..."
    )

    print()

    for index, item in enumerate(
            duplicates,
            start=1
    ):

        print(
            f"[{index}/{len(duplicates)}] "
            f"{item['video_id']} "
            f"{item['title']}"
        )

        try:

            delete_playlist_item(
                creds,
                item["playlist_item_id"]
            )

            deleted += 1

            print(
                "  -> DELETED"
            )

        except Exception as e:

            errors += 1

            print(
                f"  -> ERROR: {e}"
            )

    print()
    print(
        "=" * 70
    )
    print(
        "PLAYLIST DEDUPE FINISHED"
    )
    print(
        "=" * 70
    )
    print()
    print(
        f"Total items:       {len(items)}"
    )
    print(
        f"Unique videos:     {len(seen)}"
    )
    print(
        f"Duplicates found:  {len(duplicates)}"
    )
    print(
        f"Deleted:           {deleted}"
    )
    print(
        f"Errors:            {errors}"
    )
    print()


# ============================================================
# Process one playlist item
# ============================================================

def process_playlist_video(
        conn,
        row,
        creds,
        playlist_id
):
    youtube_id = row["youtube_id"]

    if not youtube_id:
        return "skipped"

    # --------------------------------------------------------
    # Already completed for this playlist
    # --------------------------------------------------------

    if (
            row["playlist_status"] == "completed"
            and row["playlist_id"] == playlist_id
    ):
        return "already"

    print()
    print(
        f"Video: {row['original_filename']}"
    )
    print(
        f"YouTube ID: {youtube_id}"
    )

    try:

        playlist_item_id = add_to_playlist(
            creds,
            playlist_id,
            youtube_id
        )

        timestamp = now_utc()

        conn.execute("""
                     UPDATE generic_videos
                     SET
                         playlist_id = ?,
                         playlist_status = 'completed',
                         playlist_item_id = ?,
                         error_message = NULL,
                         updated_at = ?
                     WHERE id = ?
                     """, (
                         playlist_id,
                         playlist_item_id,
                         timestamp,
                         row["id"]
                     ))

        conn.commit()

        print(
            "  -> ADDED"
        )

        return "added"

    except Exception as e:

        timestamp = now_utc()

        conn.execute("""
                     UPDATE generic_videos
                     SET
                         playlist_id = ?,
                         playlist_status = 'error',
                         error_message = ?,
                         updated_at = ?
                     WHERE id = ?
                     """, (
                         playlist_id,
                         str(e),
                         timestamp,
                         row["id"]
                     ))

        conn.commit()

        print(
            f"  -> ERROR: {e}"
        )

        return "error"


# ============================================================
# Scan command
# ============================================================

def command_scan(
        conn,
        folder
):
    files = find_video_files(
        folder
    )

    print()
    print(
        f"Found {len(files)} video file(s)."
    )
    print()

    inserted = 0
    existing = 0

    for index, path in enumerate(
            files,
            start=1
    ):

        print(
            f"[{index}/{len(files)}] {path}"
        )

        file_size = os.path.getsize(
            path
        )

        sha256 = calculate_sha256(
            path
        )

        row = get_by_sha256(
            conn,
            sha256
        )

        if row:

            existing += 1

            print(
                "  -> Already in database"
            )

        else:

            insert_or_get_file(
                conn,
                path,
                sha256,
                file_size
            )

            inserted += 1

            print(
                "  -> Added"
            )

    print()
    print(
        "SCAN COMPLETE"
    )
    print(
        f"New:      {inserted}"
    )
    print(
        f"Existing: {existing}"
    )


# ============================================================
# Upload command
# ============================================================

def command_upload(
        conn,
        folder
):
    files = find_video_files(
        folder
    )

    print()
    print(
        f"Found {len(files)} video file(s)."
    )

    if not files:
        return

    creds = get_credentials()

    for index, path in enumerate(
            files,
            start=1
    ):

        print()
        print(
            f"[{index}/{len(files)}]"
        )

        file_size = os.path.getsize(
            path
        )

        sha256 = calculate_sha256(
            path
        )

        row = insert_or_get_file(
            conn,
            path,
            sha256,
            file_size
        )

        # ----------------------------------------------------
        # Already uploaded
        # ----------------------------------------------------

        if row["youtube_status"] == "completed":

            print(
                "ALREADY UPLOADED"
            )

            print(
                f"YouTube ID: "
                f"{row['youtube_id']}"
            )

            continue

        try:

            timestamp = now_utc()

            conn.execute("""
                         UPDATE generic_videos
                         SET
                             last_attempt_at = ?,
                             updated_at = ?
                         WHERE id = ?
                         """, (
                             timestamp,
                             timestamp,
                             row["id"]
                         ))

            conn.commit()

            upload_file(
                conn,
                row,
                creds
            )

        except YouTubeUploadLimitExceeded:

            print()
            print(
                "=" * 70
            )
            print(
                "YOUTUBE UPLOAD LIMIT REACHED"
            )
            print(
                "=" * 70
            )

            conn.execute("""
                         UPDATE generic_videos
                         SET
                             youtube_status = 'blocked',
                             error_message = ?,
                             updated_at = ?
                         WHERE id = ?
                         """, (
                             "uploadLimitExceeded",
                             now_utc(),
                             row["id"]
                         ))

            conn.commit()

            print(
                "Current file marked as blocked."
            )
            print(
                "Batch stopped."
            )

            return

        except KeyboardInterrupt:

            print()
            print(
                "Upload interrupted."
            )

            conn.execute("""
                         UPDATE generic_videos
                         SET
                             youtube_status = 'paused',
                             updated_at = ?
                         WHERE id = ?
                         """, (
                             now_utc(),
                             row["id"]
                         ))

            conn.commit()

            raise

        except Exception as e:

            print()
            print(
                f"ERROR: {e}"
            )

            conn.execute("""
                         UPDATE generic_videos
                         SET
                             youtube_status = 'error',
                             error_message = ?,
                             updated_at = ?
                         WHERE id = ?
                         """, (
                             str(e),
                             now_utc(),
                             row["id"]
                         ))

            conn.commit()

    print()
    print(
        "=" * 70
    )
    print(
        "UPLOAD BATCH FINISHED"
    )
    print(
        "=" * 70
    )


# ============================================================
# Playlist command
# ============================================================

def command_playlist(
        conn,
        playlist_id
):
    print()
    print(
        f"Playlist: {playlist_id}"
    )
    print()

    rows = conn.execute("""
                        SELECT *
                        FROM generic_videos
                        WHERE
                            youtube_status = 'completed'
                          AND youtube_id IS NOT NULL
                        ORDER BY id
                        """).fetchall()

    if not rows:

        print(
            "No uploaded videos found."
        )

        return

    creds = get_credentials()

    total = len(rows)

    added = 0
    already = 0
    errors = 0

    print(
        f"Found {total} uploaded video(s)."
    )
    print()

    for index, row in enumerate(
            rows,
            start=1
    ):

        print(
            f"[{index}/{total}]"
        )

        result = process_playlist_video(
            conn,
            row,
            creds,
            playlist_id
        )

        if result == "added":
            added += 1

        elif result == "already":
            already += 1

            print(
                "  -> ALREADY IN PLAYLIST"
            )

        elif result == "error":
            errors += 1

    print()
    print(
        "=" * 70
    )
    print(
        "PLAYLIST BATCH FINISHED"
    )
    print(
        "=" * 70
    )
    print()
    print(
        f"Added:   {added}"
    )
    print(
        f"Already: {already}"
    )
    print(
        f"Errors:  {errors}"
    )
    print()


# ============================================================
# Status command
# ============================================================

def command_status(conn):

    rows = conn.execute("""
                        SELECT
                            youtube_status,
                            playlist_status,
                            COUNT(*) AS count
                        FROM generic_videos
                        GROUP BY
                            youtube_status,
                            playlist_status
                        ORDER BY
                            youtube_status,
                            playlist_status
                        """).fetchall()

    print()
    print(
        "=" * 70
    )
    print(
        "DATABASE STATUS"
    )
    print(
        "=" * 70
    )
    print()

    for row in rows:

        print(
            f"YouTube: "
            f"{row['youtube_status']:<12} "
            f"Playlist: "
            f"{row['playlist_status']:<12} "
            f"Count: "
            f"{row['count']}"
        )

    print()


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="YouTube Soccer Video Backup"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    # --------------------------------------------------------
    # scan
    # --------------------------------------------------------

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan videos and update database"
    )

    scan_parser.add_argument(
        "--folder",
        required=True,
        help="Folder to scan recursively"
    )

    # --------------------------------------------------------
    # upload
    # --------------------------------------------------------

    upload_parser = subparsers.add_parser(
        "upload",
        help="Upload videos to YouTube"
    )

    upload_parser.add_argument(
        "--folder",
        required=True,
        help="Folder to scan recursively"
    )

    # --------------------------------------------------------
    # playlist
    # --------------------------------------------------------

    playlist_parser = subparsers.add_parser(
        "playlist",
        help="Add uploaded videos to a playlist"
    )

    playlist_parser.add_argument(
        "--playlist",
        required=True,
        help="YouTube Playlist ID"
    )

    # --------------------------------------------------------
    # dedupe
    # --------------------------------------------------------

    dedupe_parser = subparsers.add_parser(
        "dedupe",
        help="Remove duplicate videos from a playlist"
    )

    dedupe_parser.add_argument(
        "--playlist",
        required=True,
        help="YouTube Playlist ID"
    )

    dedupe_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show duplicates without deleting them"
    )

    # --------------------------------------------------------
    # status
    # --------------------------------------------------------

    subparsers.add_parser(
        "status",
        help="Show database status"
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Validate folder
    # --------------------------------------------------------

    if args.command in (
            "scan",
            "upload"
    ):

        folder = os.path.abspath(
            args.folder
        )

        if not os.path.isdir(folder):

            print(
                f"ERROR: Folder does not exist: "
                f"{folder}"
            )

            sys.exit(1)

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    init_db(conn)

    try:

        if args.command == "scan":

            print()
            print(
                "=" * 70
            )
            print(
                "SCAN"
            )
            print(
                "=" * 70
            )
            print(
                f"Folder: {folder}"
            )

            command_scan(
                conn,
                folder
            )

        elif args.command == "upload":

            print()
            print(
                "=" * 70
            )
            print(
                "UPLOAD"
            )
            print(
                "=" * 70
            )
            print(
                f"Folder: {folder}"
            )

            command_upload(
                conn,
                folder
            )

        elif args.command == "playlist":

            print()
            print(
                "=" * 70
            )
            print(
                "PLAYLIST"
            )
            print(
                "=" * 70
            )

            command_playlist(
                conn,
                args.playlist
            )

        elif args.command == "dedupe":

            print()
            print(
                "=" * 70
            )
            print(
                "PLAYLIST DEDUPE"
            )
            print(
                "=" * 70
            )

            command_dedupe(
                args.playlist,
                args.dry_run
            )

        elif args.command == "status":

            command_status(
                conn
            )

    finally:

        conn.close()


if __name__ == "__main__":
    main()