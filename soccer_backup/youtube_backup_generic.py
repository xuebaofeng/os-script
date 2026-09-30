import argparse
import hashlib
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


DB_FILE = "soccer_backup.db"
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

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
# SQLite
# ============================================================

def now_utc():
    return datetime.now(timezone.utc).isoformat()


def get_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
                 CREATE TABLE IF NOT EXISTS generic_videos (
                                                               id INTEGER PRIMARY KEY AUTOINCREMENT,

                                                               original_filename TEXT NOT NULL,
                                                               original_path TEXT NOT NULL UNIQUE,

                                                               file_size INTEGER,
                                                               sha256 TEXT UNIQUE,

                                                               youtube_id TEXT,
                                                               youtube_status TEXT DEFAULT 'pending',

                                                               upload_session_url TEXT,
                                                               uploaded_bytes INTEGER DEFAULT 0,

                                                               error_message TEXT,
                                                               last_attempt_at TEXT,

                                                               created_at TEXT NOT NULL,
                                                               updated_at TEXT NOT NULL
                 )
                 """)

    conn.commit()

    return conn


# ============================================================
# SHA256
# ============================================================

def calculate_sha256(path):
    print("Calculating SHA256...")

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)

            if not data:
                break

            sha256.update(data)

    result = sha256.hexdigest()

    print(f"SHA256: {result}")

    return result


# ============================================================
# SQLite record
# ============================================================

def get_or_create_video(conn, path, sha256):
    path = str(path.resolve())
    filename = Path(path).name
    file_size = os.path.getsize(path)
    now = now_utc()

    row = conn.execute("""
                       SELECT *
                       FROM generic_videos
                       WHERE original_path = ?
                       """, (path,)).fetchone()

    if row:
        return row

    # Same file content may already exist under another path.
    row = conn.execute("""
                       SELECT *
                       FROM generic_videos
                       WHERE sha256 = ?
                       """, (sha256,)).fetchone()

    if row:
        return row

    conn.execute("""
                 INSERT INTO generic_videos (
                     original_filename,
                     original_path,
                     file_size,
                     sha256,
                     youtube_status,
                     created_at,
                     updated_at
                 )
                 VALUES (?, ?, ?, ?, 'pending', ?, ?)
                 """, (
                     filename,
                     path,
                     file_size,
                     sha256,
                     now,
                     now
                 ))

    conn.commit()

    return conn.execute("""
                        SELECT *
                        FROM generic_videos
                        WHERE original_path = ?
                        """, (path,)).fetchone()


# ============================================================
# OAuth
# ============================================================

def get_credentials():
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing Google OAuth token...")
        creds.refresh(Request())

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


# ============================================================
# YouTube HTTP helpers
# ============================================================

UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
)


def get_access_token(creds):
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds.token


def create_upload_session(creds, title, description):
    token = get_access_token(creds)

    params = {
        "uploadType": "resumable",
        "part": "snippet,status",
    }

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "17",
        },
        "status": {
            "privacyStatus": "private",
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*",
    }

    response = requests.post(
        UPLOAD_URL,
        params=params,
        headers=headers,
        json=body,
        timeout=60,
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Create upload session failed: "
            f"{response.status_code} {response.text}"
        )

    location = response.headers.get("Location")

    if not location:
        raise RuntimeError(
            "YouTube did not return upload session URL."
        )

    return location


def query_upload_position(creds, session_url, file_size):
    token = get_access_token(creds)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Length": "0",
        "Content-Range": f"bytes */{file_size}",
    }

    response = requests.put(
        session_url,
        headers=headers,
        timeout=60,
    )

    if response.status_code in (200, 201):
        return file_size, response

    if response.status_code == 308:
        range_header = response.headers.get("Range")

        if not range_header:
            return 0, response

        # Example:
        # Range: bytes=0-49283071
        end = int(range_header.split("-")[-1])

        return end + 1, response

    if response.status_code in (404, 410):
        raise RuntimeError("UPLOAD_SESSION_EXPIRED")

    if response.status_code == 401:
        creds.refresh(Request())
        return query_upload_position(
            creds,
            session_url,
            file_size
        )

    raise RuntimeError(
        f"Query upload position failed: "
        f"{response.status_code} {response.text}"
    )


# ============================================================
# Upload
# ============================================================

def upload_file(
        conn,
        creds,
        row,
        title,
        description
):
    path = Path(row["original_path"])
    file_size = row["file_size"]

    session_url = row["upload_session_url"]

    # --------------------------------------------------------
    # Create session if necessary
    # --------------------------------------------------------

    if not session_url:
        print("Creating YouTube resumable upload session...")

        session_url = create_upload_session(
            creds,
            title,
            description
        )

        conn.execute("""
                     UPDATE generic_videos
                     SET
                         upload_session_url = ?,
                         uploaded_bytes = 0,
                         youtube_status = 'uploading',
                         error_message = NULL,
                         last_attempt_at = ?,
                         updated_at = ?
                     WHERE id = ?
                     """, (
                         session_url,
                         now_utc(),
                         now_utc(),
                         row["id"]
                     ))

        conn.commit()

    # --------------------------------------------------------
    # Ask YouTube where the upload currently is
    # --------------------------------------------------------

    try:
        uploaded_bytes, response = query_upload_position(
            creds,
            session_url,
            file_size
        )

        # 200/201 means upload is already complete.
        if response.status_code in (200, 201):
            video_id = response.json()["id"]

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
                             video_id,
                             file_size,
                             now_utc(),
                             row["id"]
                         ))

            conn.commit()

            return video_id

    except RuntimeError as e:
        if str(e) == "UPLOAD_SESSION_EXPIRED":
            print("Upload session expired. Creating a new one...")

            session_url = create_upload_session(
                creds,
                title,
                description
            )

            uploaded_bytes = 0

            conn.execute("""
                         UPDATE generic_videos
                         SET
                             upload_session_url = ?,
                             uploaded_bytes = 0,
                             youtube_status = 'uploading',
                             error_message = NULL,
                             updated_at = ?
                         WHERE id = ?
                         """, (
                             session_url,
                             now_utc(),
                             row["id"]
                         ))

            conn.commit()

        else:
            raise

    print(
        f"Resume position: "
        f"{uploaded_bytes:,} / {file_size:,} bytes"
    )

    # --------------------------------------------------------
    # Upload chunks
    # --------------------------------------------------------

    with open(path, "rb") as f:

        f.seek(uploaded_bytes)

        position = uploaded_bytes

        while position < file_size:

            chunk = f.read(CHUNK_SIZE)

            if not chunk:
                break

            chunk_start = position
            chunk_end = position + len(chunk) - 1

            for attempt in range(5):

                try:
                    token = get_access_token(creds)

                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Length": str(len(chunk)),
                        "Content-Range":
                            f"bytes {chunk_start}-"
                            f"{chunk_end}/{file_size}",
                    }

                    response = requests.put(
                        session_url,
                        headers=headers,
                        data=chunk,
                        timeout=300,
                    )

                    if response.status_code in (200, 201):
                        video_id = response.json()["id"]

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
                                         video_id,
                                         file_size,
                                         now_utc(),
                                         row["id"]
                                     ))

                        conn.commit()

                        print()
                        print(
                            f"UPLOAD COMPLETE: {video_id}"
                        )

                        return video_id

                    if response.status_code == 308:
                        position = chunk_end + 1

                        conn.execute("""
                                     UPDATE generic_videos
                                     SET
                                         uploaded_bytes = ?,
                                         youtube_status = 'uploading',
                                         last_attempt_at = ?,
                                         updated_at = ?
                                     WHERE id = ?
                                     """, (
                                         position,
                                         now_utc(),
                                         now_utc(),
                                         row["id"]
                                     ))

                        conn.commit()

                        percent = (
                                position * 100 / file_size
                        )

                        print(
                            f"\rUploaded "
                            f"{position:,}/{file_size:,} "
                            f"({percent:.1f}%)",
                            end="",
                            flush=True
                        )

                        break

                    if response.status_code == 401:
                        print(
                            "\nOAuth token expired. Refreshing..."
                        )

                        creds.refresh(Request())

                        continue

                    if response.status_code in (404, 410):
                        raise RuntimeError(
                            "UPLOAD_SESSION_EXPIRED"
                        )

                    raise RuntimeError(
                        f"Upload failed: "
                        f"{response.status_code} "
                        f"{response.text}"
                    )

                except requests.RequestException as e:

                    if attempt == 4:
                        raise

                    wait = 2 ** attempt

                    print(
                        f"\nNetwork error: {e}"
                    )

                    print(
                        f"Retrying in {wait}s..."
                    )

                    time.sleep(wait)

            else:
                raise RuntimeError(
                    "Failed to upload chunk."
                )

    raise RuntimeError(
        "Upload ended without YouTube completion."
    )


# ============================================================
# Description
# ============================================================

def build_description(filename, sha256, source):
    return (
        "Video Backup\n\n"
        f"File: {filename}\n"
        f"SHA256: {sha256}\n"
        f"Source: {source}\n"
    )


# ============================================================
# Single file
# ============================================================

def process_file(conn, creds, path, source):
    path = Path(path)

    print()
    print("=" * 70)
    print(f"File: {path}")

    if not path.exists():
        print("ERROR: File does not exist.")
        return

    sha256 = calculate_sha256(path)

    # --------------------------------------------------------
    # Check SHA256 first
    # --------------------------------------------------------

    existing = conn.execute("""
                            SELECT *
                            FROM generic_videos
                            WHERE sha256 = ?
                            """, (sha256,)).fetchone()

    if existing:

        if existing["youtube_status"] == "completed":
            print(
                "ALREADY UPLOADED"
            )
            print(
                f"YouTube ID: "
                f"{existing['youtube_id']}"
            )
            return

        row = existing

        print(
            f"Existing DB record: "
            f"id={row['id']}"
        )

    else:

        row = get_or_create_video(
            conn,
            path,
            sha256
        )

    # --------------------------------------------------------
    # Already completed
    # --------------------------------------------------------

    if row["youtube_status"] == "completed":
        print("ALREADY UPLOADED")
        print(
            f"YouTube ID: "
            f"{row['youtube_id']}"
        )
        return

    title = path.name

    description = build_description(
        path.name,
        sha256,
        source
    )

    print()
    print(f"TITLE: {title}")

    print()
    print("DESCRIPTION:")
    print(description)

    try:

        video_id = upload_file(
            conn,
            creds,
            row,
            title,
            description
        )

        print()
        print(
            f"YouTube URL: "
            f"https://www.youtube.com/watch?v={video_id}"
        )

    except KeyboardInterrupt:

        print()
        print(
            "Upload interrupted. "
            "Run the same command again to resume."
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
        print(f"ERROR: {e}")

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


# ============================================================
# Folder
# ============================================================

def scan_folder(folder):
    folder = Path(folder)

    files = []

    for path in folder.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        files.append(path)

    files.sort(
        key=lambda p: str(p).lower()
    )

    return files


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generic YouTube video backup "
            "with SHA256 deduplication "
            "and resumable uploads."
        )
    )

    parser.add_argument(
        "--folder",
        required=True,
        help="Folder to recursively scan"
    )

    parser.add_argument(
        "--db",
        default=DB_FILE,
        help=f"SQLite DB (default: {DB_FILE})"
    )

    parser.add_argument(
        "--source",
        default="mustang18",
        help="Source name"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate hashes and show files only"
    )

    args = parser.parse_args()

    folder = Path(args.folder)

    if not folder.exists():
        print(
            f"ERROR: Folder does not exist: "
            f"{folder}"
        )
        sys.exit(1)

    conn = get_db(args.db)

    try:

        files = scan_folder(folder)

        print(
            f"Found {len(files)} video file(s)."
        )

        if not files:
            return

        creds = None

        if not args.dry_run:
            creds = get_credentials()

        for index, path in enumerate(files, 1):

            print()
            print(
                f"[{index}/{len(files)}]"
            )

            if args.dry_run:
                sha256 = calculate_sha256(path)

                print(
                    f"File: {path.name}"
                )
                print(
                    f"SHA256: {sha256}"
                )

                continue

            process_file(
                conn,
                creds,
                path,
                args.source
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()