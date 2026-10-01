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

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable"
    "&part=snippet,status"
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

                                                               upload_session_url TEXT,
                                                               uploaded_bytes INTEGER DEFAULT 0,

                                                               error_message TEXT,
                                                               last_attempt_at TEXT,

                                                               created_at TEXT NOT NULL,
                                                               updated_at TEXT NOT NULL
                 )
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


def insert_or_get_file(
        conn,
        path,
        sha256,
        file_size
):
    filename = os.path.basename(path)
    timestamp = now_utc()

    row = get_by_sha256(conn, sha256)

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
                     timestamp,
                     timestamp
                 ))

    conn.commit()

    return get_by_sha256(conn, sha256)


# ============================================================
# OAuth
# ============================================================

def get_credentials():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing YouTube credentials...")
        creds.refresh(Request())

    if not creds or not creds.valid:

        print()
        print("YouTube authorization required.")
        print()

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


# ============================================================
# YouTube metadata
# ============================================================

def build_title(filename):
    # YouTube title = original filename
    return filename


def build_description(filename, sha256, source):
    return (
        "Video Backup\n"
        "\n"
        f"File: {filename}\n"
        f"SHA256: {sha256}\n"
        f"Source: {source}\n"
    )


# ============================================================
# Create resumable upload session
# ============================================================

def create_upload_session(
        creds,
        filename,
        sha256,
        source,
        file_size
):
    title = build_title(filename)

    description = build_description(
        filename,
        sha256,
        source
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "17",
        },
        "status": {
            "privacyStatus": "private"
        }
    }

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/*",
    }

    response = requests.post(
        UPLOAD_URL,
        headers=headers,
        json=body,
        timeout=60
    )

    if response.status_code not in (200, 201):

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
# Upload resumable file
# ============================================================

def upload_file(
        conn,
        row,
        creds,
        source
):
    path = row["original_path"]
    filename = row["original_filename"]
    sha256 = row["sha256"]
    file_size = row["file_size"]

    session_url = row["upload_session_url"]
    uploaded_bytes = row["uploaded_bytes"] or 0

    # --------------------------------------------------------
    # Create upload session if necessary
    # --------------------------------------------------------

    if not session_url:

        print()
        print(
            "Creating YouTube resumable upload session..."
        )

        session_url = create_upload_session(
            creds,
            filename,
            sha256,
            source,
            file_size
        )

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
                         now_utc(),
                         now_utc(),
                         row["id"]
                     ))

        conn.commit()

        uploaded_bytes = 0

    # --------------------------------------------------------
    # Upload chunks
    # --------------------------------------------------------

    print()
    print(f"Uploading: {filename}")
    print(f"Size: {file_size:,} bytes")
    print(f"Already uploaded: {uploaded_bytes:,} bytes")
    print()

    with open(path, "rb") as f:

        if uploaded_bytes:
            f.seek(uploaded_bytes)

        while uploaded_bytes < file_size:

            chunk = f.read(CHUNK_SIZE)

            if not chunk:
                break

            chunk_start = uploaded_bytes
            chunk_end = (
                    uploaded_bytes
                    + len(chunk)
                    - 1
            )

            headers = {
                "Content-Length": str(len(chunk)),
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
            # Upload completed
            # ------------------------------------------------

            if response.status_code in (
                    200,
                    201
            ):

                data = response.json()

                youtube_id = data["id"]

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
                                 now_utc(),
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
            # Chunk accepted but upload not complete
            # ------------------------------------------------

            if response.status_code == 308:

                range_header = response.headers.get(
                    "Range"
                )

                if range_header:

                    # Example:
                    # Range: bytes=0-8388607

                    last_byte = int(
                        range_header.split("-")[-1]
                    )

                    uploaded_bytes = (
                            last_byte + 1
                    )

                else:
                    uploaded_bytes = (
                            chunk_end + 1
                    )

                conn.execute("""
                             UPDATE generic_videos
                             SET
                                 uploaded_bytes = ?,
                                 last_attempt_at = ?,
                                 updated_at = ?
                             WHERE id = ?
                             """, (
                                 uploaded_bytes,
                                 now_utc(),
                                 now_utc(),
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
            # Upload session expired / invalid
            # ------------------------------------------------

            if response.status_code in (
                    404,
                    410
            ):

                conn.execute("""
                             UPDATE generic_videos
                             SET
                                 upload_session_url = NULL,
                                 uploaded_bytes = 0,
                                 updated_at = ?
                             WHERE id = ?
                             """, (
                                 now_utc(),
                                 row["id"]
                             ))

                conn.commit()

                raise RuntimeError(
                    "YouTube upload session expired "
                    "or is no longer valid."
                )

            # ------------------------------------------------
            # Other errors
            # ------------------------------------------------

            raise RuntimeError(
                "YouTube upload failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

    raise RuntimeError(
        "Upload ended before YouTube returned "
        "a completed video ID."
    )


# ============================================================
# Process one file
# ============================================================

def process_file(
        conn,
        creds,
        path,
        source
):
    filename = os.path.basename(path)

    print()
    print("=" * 70)
    print(filename)
    print("=" * 70)

    file_size = os.path.getsize(path)

    sha256 = calculate_sha256(path)

    print(f"SHA256: {sha256}")
    print(f"Size:   {file_size:,}")

    row = insert_or_get_file(
        conn,
        path,
        sha256,
        file_size
    )

    # --------------------------------------------------------
    # Already uploaded
    # --------------------------------------------------------

    if row["youtube_status"] == "completed":

        print()
        print("ALREADY UPLOADED")

        if row["youtube_id"]:
            print(
                f"YouTube ID: "
                f"{row['youtube_id']}"
            )

        return True

    # --------------------------------------------------------
    # Attempt upload
    # --------------------------------------------------------

    try:

        conn.execute("""
                     UPDATE generic_videos
                     SET
                         last_attempt_at = ?,
                         updated_at = ?
                     WHERE id = ?
                     """, (
                         now_utc(),
                         now_utc(),
                         row["id"]
                     ))

        conn.commit()

        upload_file(
            conn,
            row,
            creds,
            source
        )

        return True

    # --------------------------------------------------------
    # YouTube account upload limit
    # --------------------------------------------------------

    except YouTubeUploadLimitExceeded:

        print()
        print("=" * 70)
        print("YOUTUBE UPLOAD LIMIT REACHED")
        print("=" * 70)
        print()
        print(
            "YouTube has rejected the upload because "
            "the account has reached its upload limit."
        )
        print()
        print(
            "This file has been marked as BLOCKED."
        )
        print(
            "The entire batch will stop now."
        )
        print()
        print(
            "Run the same command again later."
        )
        print()

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

        return False

    # --------------------------------------------------------
    # Ctrl+C
    # --------------------------------------------------------

    except KeyboardInterrupt:

        print()
        print()
        print(
            "Upload interrupted."
        )
        print(
            "The resumable upload state has been saved."
        )
        print(
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

    # --------------------------------------------------------
    # Other errors
    # --------------------------------------------------------

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

        return True


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Recursively backup generic videos "
            "to YouTube."
        )
    )

    parser.add_argument(
        "--folder",
        required=True,
        help="Folder to scan recursively"
    )

    parser.add_argument(
        "--source",
        default="mustang18",
        help="Source name"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate hashes only"
    )

    args = parser.parse_args()

    folder = os.path.abspath(
        args.folder
    )

    if not os.path.isdir(folder):

        print(
            f"ERROR: Folder does not exist: "
            f"{folder}"
        )

        sys.exit(1)

    print()
    print("=" * 70)
    print("Generic YouTube Backup")
    print("=" * 70)
    print()
    print(f"Folder: {folder}")
    print(f"Source: {args.source}")
    print()

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    init_db(conn)

    # --------------------------------------------------------
    # Find files
    # --------------------------------------------------------

    files = find_video_files(
        folder
    )

    print(
        f"Found {len(files)} video file(s)."
    )
    print()

    if not files:
        conn.close()
        return

    # --------------------------------------------------------
    # Dry run
    # --------------------------------------------------------

    if args.dry_run:

        print(
            "DRY RUN - no database changes "
            "and no uploads."
        )
        print()

        for path in files:

            file_size = os.path.getsize(
                path
            )

            sha256 = calculate_sha256(
                path
            )

            print()
            print(
                f"File:   {path}"
            )
            print(
                f"Size:   {file_size:,}"
            )
            print(
                f"SHA256: {sha256}"
            )

        conn.close()
        return

    # --------------------------------------------------------
    # OAuth
    # --------------------------------------------------------

    creds = get_credentials()

    # --------------------------------------------------------
    # Process files
    # --------------------------------------------------------

    for index, path in enumerate(
            files,
            start=1
    ):

        print()
        print(
            f"[{index}/{len(files)}]"
        )

        result = process_file(
            conn,
            creds,
            path,
            args.source
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # uploadLimitExceeded stops entire batch
        # ----------------------------------------------------

        if result is False:

            print()
            print("=" * 70)
            print("BATCH STOPPED")
            print("=" * 70)
            print()
            print(
                "YouTube upload limit has been reached."
            )
            print()
            print(
                "Already completed files remain marked "
                "as completed."
            )
            print(
                "The current file is marked as blocked."
            )
            print(
                "Remaining files were not attempted."
            )
            print()
            print(
                "Run the same command again later."
            )
            print()

            conn.close()
            return

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("BACKUP FINISHED")
    print("=" * 70)
    print()

    conn.close()


if __name__ == "__main__":
    main()