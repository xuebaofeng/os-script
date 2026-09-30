import argparse
import hashlib
import json
import sqlite3
import sys
import time
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

UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv"
}


# ============================================================
# SQLite helpers
# ============================================================

def connect_db(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_columns(conn):
    """
    Add upload-state columns to the existing videos table.

    This does NOT delete or recreate the database.
    """

    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(videos)"
        ).fetchall()
    }

    additions = {
        "upload_session_url":
            "TEXT",

        "uploaded_bytes":
            "INTEGER DEFAULT 0",

        "error_message":
            "TEXT",

        "last_attempt_at":
            "TEXT"
    }

    for name, definition in additions.items():
        if name not in columns:
            print(
                f"Adding videos.{name} ..."
            )

            conn.execute(
                f"""
                ALTER TABLE videos
                ADD COLUMN {name} {definition}
                """
            )

    conn.commit()


# ============================================================
# File
# ============================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


# ============================================================
# Database lookup
# ============================================================

def find_video(conn, filename, filepath):
    """
    Authoritative association is SQLite.

    First:
        original_path

    Fallback:
        original_filename, but only if exactly one row exists.
    """

    rows = conn.execute(
        """
        SELECT
            v.id,
            v.game_id,
            v.original_filename,
            v.original_path,
            v.period,
            v.file_size,
            v.sha256,
            v.youtube_id,
            v.youtube_status,
            v.upload_session_url,
            v.uploaded_bytes,
            v.error_message,

            m.full_date,
            m.division_title,

            m.home_team_title,
            m.home_team_abbr,
            m.home_score,

            m.away_team_title,
            m.away_team_abbr,
            m.away_score

        FROM videos v

                 JOIN matches m
                      ON m.game_id = v.game_id

        WHERE v.original_path = ?

            LIMIT 1
        """,
        (filepath,)
    ).fetchall()

    if rows:
        return rows[0]

    rows = conn.execute(
        """
        SELECT
            v.id,
            v.game_id,
            v.original_filename,
            v.original_path,
            v.period,
            v.file_size,
            v.sha256,
            v.youtube_id,
            v.youtube_status,
            v.upload_session_url,
            v.uploaded_bytes,
            v.error_message,

            m.full_date,
            m.division_title,

            m.home_team_title,
            m.home_team_abbr,
            m.home_score,

            m.away_team_title,
            m.away_team_abbr,
            m.away_score

        FROM videos v

                 JOIN matches m
                      ON m.game_id = v.game_id

        WHERE v.original_filename = ?

            LIMIT 2
        """,
        (filename,)
    ).fetchall()

    if len(rows) == 1:
        return rows[0]

    if len(rows) > 1:
        raise RuntimeError(
            "More than one SQLite record has this filename. "
            "Use the exact original_path."
        )

    return None


def find_sha_duplicate(conn, sha256):
    return conn.execute(
        """
        SELECT
            id,
            game_id,
            original_filename,
            original_path,
            youtube_id,
            youtube_status
        FROM videos
        WHERE sha256 = ?
            LIMIT 1
        """,
        (sha256,)
    ).fetchone()


def update_sha256(
        conn,
        video_id,
        sha256,
        file_size
):
    conn.execute(
        """
        UPDATE videos
        SET
            sha256 = ?,
            file_size = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            sha256,
            file_size,
            video_id
        )
    )

    conn.commit()


def save_session(
        conn,
        video_id,
        session_url
):
    conn.execute(
        """
        UPDATE videos
        SET
            upload_session_url = ?,
            uploaded_bytes = 0,
            youtube_status = 'uploading',
            last_attempt_at = datetime('now'),
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            session_url,
            video_id
        )
    )

    conn.commit()


def save_progress(
        conn,
        video_id,
        uploaded_bytes
):
    conn.execute(
        """
        UPDATE videos
        SET
            uploaded_bytes = ?,
            youtube_status = 'uploading',
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            uploaded_bytes,
            video_id
        )
    )

    conn.commit()


def clear_session(
        conn,
        video_id
):
    conn.execute(
        """
        UPDATE videos
        SET
            upload_session_url = NULL,
            uploaded_bytes = 0,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (video_id,)
    )

    conn.commit()


def mark_completed(
        conn,
        video_id,
        youtube_id
):
    conn.execute(
        """
        UPDATE videos
        SET
            youtube_id = ?,
            youtube_status = 'completed',
            upload_session_url = NULL,
            uploaded_bytes = 0,
            error_message = NULL,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            youtube_id,
            video_id
        )
    )

    conn.commit()


def mark_failed(
        conn,
        video_id,
        message
):
    conn.execute(
        """
        UPDATE videos
        SET
            youtube_status = 'failed',
            error_message = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            message,
            video_id
        )
    )

    conn.commit()


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

        with open(
                TOKEN_FILE,
                "w",
                encoding="utf-8"
        ) as f:
            f.write(creds.to_json())

    if not creds or not creds.valid:
        print("Starting Google OAuth...")

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        with open(
                TOKEN_FILE,
                "w",
                encoding="utf-8"
        ) as f:
            f.write(creds.to_json())

    return creds


# ============================================================
# YouTube metadata
# ============================================================

def team_display(title, abbr):
    if title and abbr:
        return f"{title} ({abbr})"

    return title or abbr or ""


def format_date(full_date):
    if not full_date:
        return ""

    return full_date[:10]


def build_title(match, period):
    home = team_display(
        match["home_team_title"],
        match["home_team_abbr"]
    )

    away = team_display(
        match["away_team_title"],
        match["away_team_abbr"]
    )

    date = format_date(
        match["full_date"]
    )

    parts = [
        home,
        "vs",
        away
    ]

    if date:
        parts.append(date)

    if (
            match["home_score"] is not None
            and match["away_score"] is not None
    ):
        parts.append(
            f"{match['home_score']}-"
            f"{match['away_score']}"
        )

    if period:
        parts.append(period)

    return " | ".join(parts)


def build_description(match, period):
    home = team_display(
        match["home_team_title"],
        match["home_team_abbr"]
    )

    away = team_display(
        match["away_team_title"],
        match["away_team_abbr"]
    )

    lines = [
        "Youth Soccer Match Video",
        "",
        f"Match Date: "
        f"{format_date(match['full_date'])}",
        f"Match: {home} vs {away}",
    ]

    if (
            match["home_score"] is not None
            and match["away_score"] is not None
    ):
        lines.append(
            f"Score: "
            f"{match['home_score']}-"
            f"{match['away_score']}"
        )

    if period:
        lines.append(
            f"Period: {period}"
        )

    if match["division_title"]:
        lines.append(
            f"Competition: "
            f"{match['division_title']}"
        )

    lines.extend([
        "",
        f"Trace Game ID: {match['game_id']}",
        "Source: Trace",
        "",
        "Archived for personal soccer "
        "video backup and analysis."
    ])

    return "\n".join(lines)


def build_tags(match, period):
    tags = []

    def add(value):
        if value and value not in tags:
            tags.append(value)

    add(match["home_team_title"])
    add(match["home_team_abbr"])

    add(match["away_team_title"])
    add(match["away_team_abbr"])

    add(match["division_title"])

    add("soccer")
    add("youth soccer")
    add("MLS NEXT")
    add("MLS Next U15")
    add("U15")

    add(format_date(match["full_date"]))

    add(period)

    return tags


# ============================================================
# Resumable upload
# ============================================================

def create_upload_session(
        session,
        metadata,
        file_size,
        content_type
):
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length":
            str(file_size),
        "X-Upload-Content-Type":
            content_type
    }

    response = session.post(
        UPLOAD_URL,
        headers=headers,
        json=metadata,
        timeout=120
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            "Failed to create YouTube upload session:\n"
            f"HTTP {response.status_code}\n"
            f"{response.text}"
        )

    location = response.headers.get(
        "Location"
    )

    if not location:
        raise RuntimeError(
            "YouTube did not return an upload session URL."
        )

    return location


def parse_range(response):
    value = response.headers.get(
        "Range"
    )

    if not value:
        return None

    # Example:
    # bytes=0-8388607

    try:
        last_byte = int(
            value.split("-")[-1]
        )

        return last_byte + 1

    except Exception:
        return None


def query_upload_position(
        session,
        session_url,
        file_size
):
    headers = {
        "Content-Length": "0",
        "Content-Range":
            f"bytes */{file_size}"
    }

    response = session.put(
        session_url,
        headers=headers,
        timeout=120
    )

    if response.status_code == 308:
        position = parse_range(response)

        if position is None:
            return 0

        return position

    if response.status_code in (200, 201):
        return file_size

    if response.status_code in (
            404,
            410
    ):
        return None

    raise RuntimeError(
        "Failed to query upload position:\n"
        f"HTTP {response.status_code}\n"
        f"{response.text}"
    )


def upload_chunks(
        session,
        session_url,
        file_path,
        file_size,
        start_offset,
        conn,
        video_id
):
    offset = start_offset

    with open(
            file_path,
            "rb"
    ) as f:

        f.seek(offset)

        while offset < file_size:

            data = f.read(
                min(
                    CHUNK_SIZE,
                    file_size - offset
                )
            )

            if not data:
                break

            chunk_start = offset
            chunk_end = (
                    offset +
                    len(data) -
                    1
            )

            headers = {
                "Content-Length":
                    str(len(data)),

                "Content-Range":
                    (
                        f"bytes "
                        f"{chunk_start}-"
                        f"{chunk_end}/"
                        f"{file_size}"
                    )
            }

            retry = 0

            while True:
                try:
                    response = session.put(
                        session_url,
                        headers=headers,
                        data=data,
                        timeout=300
                    )

                    break

                except requests.RequestException as e:
                    retry += 1

                    if retry > 8:
                        raise RuntimeError(
                            f"Network error after retries: {e}"
                        )

                    wait = min(
                        2 ** retry,
                        60
                    )

                    print()
                    print(
                        f"Network error. "
                        f"Retrying in {wait}s..."
                    )

                    time.sleep(wait)

            # Upload complete.
            if response.status_code in (
                    200,
                    201
            ):
                result = response.json()

                youtube_id = result.get(
                    "id"
                )

                if not youtube_id:
                    raise RuntimeError(
                        "YouTube completed upload "
                        "but returned no video ID."
                    )

                save_progress(
                    conn,
                    video_id,
                    file_size
                )

                return youtube_id

            # Chunk accepted.
            if response.status_code == 308:
                server_position = parse_range(
                    response
                )

                if server_position is None:
                    offset = chunk_end + 1
                else:
                    offset = server_position

                save_progress(
                    conn,
                    video_id,
                    offset
                )

                f.seek(offset)

                percent = (
                        offset *
                        100 /
                        file_size
                )

                print(
                    f"\rUploaded: "
                    f"{percent:6.2f}% "
                    f"({offset:,}/"
                    f"{file_size:,} bytes)",
                    end="",
                    flush=True
                )

                continue

            # Session expired.
            if response.status_code in (
                    404,
                    410
            ):
                raise RuntimeError(
                    "UPLOAD_SESSION_EXPIRED"
                )

            # Token expired / auth issue.
            if response.status_code == 401:
                print()
                print(
                    "OAuth token expired. "
                    "Refreshing..."
                )

                session.auth = None

                raise RuntimeError(
                    "AUTH_REFRESH_REQUIRED"
                )

            # Temporary Google error.
            if response.status_code in (
                    429,
                    500,
                    502,
                    503,
                    504
            ):
                retry += 1

                if retry > 8:
                    raise RuntimeError(
                        "Too many YouTube server errors:\n"
                        f"{response.text}"
                    )

                wait = min(
                    2 ** retry,
                    60
                )

                print()
                print(
                    f"YouTube HTTP "
                    f"{response.status_code}. "
                    f"Retrying in {wait}s..."
                )

                time.sleep(wait)

                continue

            raise RuntimeError(
                "YouTube upload failed:\n"
                f"HTTP {response.status_code}\n"
                f"{response.text}"
            )

    raise RuntimeError(
        "Upload ended without a YouTube video ID."
    )


def resumable_upload(
        creds,
        conn,
        video_id,
        file_path,
        metadata,
        existing_session_url
):
    file_size = file_path.stat().st_size

    session = requests.Session()

    session.headers.update({
        "Authorization":
            f"Bearer {creds.token}"
    })

    session_url = existing_session_url

    # --------------------------------------------------------
    # Existing session
    # --------------------------------------------------------

    if session_url:
        print()
        print(
            "Existing YouTube upload session found."
        )

        print(
            "Checking server-side upload position..."
        )

        try:
            offset = query_upload_position(
                session,
                session_url,
                file_size
            )

        except requests.RequestException:
            offset = None

        if offset is None:
            print(
                "Existing upload session is no longer valid."
            )

            session_url = None

            clear_session(
                conn,
                video_id
            )

        else:
            print(
                f"Server says upload position: "
                f"{offset:,} bytes"
            )

    # --------------------------------------------------------
    # New session
    # --------------------------------------------------------

    if not session_url:
        print()
        print(
            "Creating new YouTube upload session..."
        )

        session_url = create_upload_session(
            session,
            metadata,
            file_size,
            "video/quicktime"
            if file_path.suffix.lower() == ".mov"
            else "video/mp4"
        )

        save_session(
            conn,
            video_id,
            session_url
        )

        offset = 0

        print(
            "Upload session saved to SQLite."
        )

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    while True:

        try:
            youtube_id = upload_chunks(
                session,
                session_url,
                file_path,
                file_size,
                offset,
                conn,
                video_id
            )

            return youtube_id

        except RuntimeError as e:

            if str(e) == "UPLOAD_SESSION_EXPIRED":
                print()
                print(
                    "Upload session expired."
                )

                clear_session(
                    conn,
                    video_id
                )

                # Create a fresh session.
                session_url = create_upload_session(
                    session,
                    metadata,
                    file_size,
                    "video/quicktime"
                    if file_path.suffix.lower() == ".mov"
                    else "video/mp4"
                )

                save_session(
                    conn,
                    video_id,
                    session_url
                )

                offset = 0

                print(
                    "New upload session created."
                )

                continue

            if str(e) == "AUTH_REFRESH_REQUIRED":
                raise

            raise


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "filename"
    )

    parser.add_argument(
        "--db",
        default=DB_FILE
    )

    args = parser.parse_args()

    file_path = Path(
        args.filename
    ).resolve()

    if not file_path.is_file():
        raise SystemExit(
            f"ERROR: File not found:\n"
            f"{file_path}"
        )

    if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise SystemExit(
            f"ERROR: Unsupported video extension: "
            f"{file_path.suffix}"
        )

    filename = file_path.name
    filepath = str(file_path)

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    conn = connect_db(
        args.db
    )

    try:
        ensure_columns(
            conn
        )

        video = find_video(
            conn,
            filename,
            filepath
        )

        if video is None:
            raise SystemExit(
                "\nERROR:\n"
                "This video has not been imported "
                "into SQLite.\n\n"
                "Run trace_import.py first.\n"
                "The uploader will NOT guess the "
                "Trace Game ID from the filename."
            )

        video_id = video["id"]
        game_id = video["game_id"]

        print()
        print(
            f"SQLite video ID : {video_id}"
        )

        print(
            f"Trace Game ID   : {game_id}"
        )

        print(
            f"Period          : "
            f"{video['period'] or 'UNKNOWN'}"
        )

        # ----------------------------------------------------
        # SHA256
        # ----------------------------------------------------

        print()
        print(
            f"Calculating SHA256: {file_path}"
        )

        sha256 = sha256_file(
            file_path
        )

        print(
            f"SHA256: {sha256}"
        )

        # ----------------------------------------------------
        # SHA duplicate
        # ----------------------------------------------------

        duplicate = find_sha_duplicate(
            conn,
            sha256
        )

        if duplicate and duplicate["id"] != video_id:

            print()
            print(
                "DUPLICATE FILE"
            )

            print(
                f"Existing SQLite ID: "
                f"{duplicate['id']}"
            )

            print(
                f"Existing Game ID: "
                f"{duplicate['game_id']}"
            )

            print(
                f"Existing YouTube ID: "
                f"{duplicate['youtube_id']}"
            )

            return

        if video["sha256"] != sha256:
            update_sha256(
                conn,
                video_id,
                sha256,
                file_path.stat().st_size
            )

        # ----------------------------------------------------
        # Already completed
        # ----------------------------------------------------

        if video["youtube_id"]:
            print()
            print(
                "ALREADY UPLOADED"
            )

            print(
                f"YouTube ID: "
                f"{video['youtube_id']}"
            )

            print(
                "https://www.youtube.com/watch?v="
                f"{video['youtube_id']}"
            )

            return

        # ----------------------------------------------------
        # Match metadata
        # ----------------------------------------------------

        match = {
            "game_id":
                video["game_id"],

            "full_date":
                video["full_date"],

            "division_title":
                video["division_title"],

            "home_team_title":
                video["home_team_title"],

            "home_team_abbr":
                video["home_team_abbr"],

            "home_score":
                video["home_score"],

            "away_team_title":
                video["away_team_title"],

            "away_team_abbr":
                video["away_team_abbr"],

            "away_score":
                video["away_score"]
        }

        period = video["period"]

        title = build_title(
            match,
            period
        )

        description = build_description(
            match,
            period
        )

        tags = build_tags(
            match,
            period
        )

        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "17"
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False
            }
        }

        # ----------------------------------------------------
        # Display metadata
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("YouTube metadata")
        print("=" * 70)

        print()
        print("TITLE:")
        print(title)

        print()
        print("TAGS:")
        print(", ".join(tags))

        print()
        print("DESCRIPTION:")
        print(description)

        print()
        print(
            "Privacy: PRIVATE"
        )

        # ----------------------------------------------------
        # OAuth
        # ----------------------------------------------------

        creds = get_credentials()

        # ----------------------------------------------------
        # Existing resumable session
        # ----------------------------------------------------

        existing_session_url = (
            video["upload_session_url"]
        )

        if existing_session_url:
            print()
            print(
                "RESUMABLE UPLOAD"
            )

            print(
                "A previous upload session exists."
            )

            print(
                "The upload will attempt to continue "
                "from the existing session."
            )

        else:
            print()
            print(
                "RESUMABLE UPLOAD"
            )

            print(
                "No previous upload session."
            )

            print(
                "A new session will be created."
            )

        # ----------------------------------------------------
        # Upload
        # ----------------------------------------------------

        try:
            youtube_id = resumable_upload(
                creds,
                conn,
                video_id,
                file_path,
                metadata,
                existing_session_url
            )

        except KeyboardInterrupt:
            print()
            print()
            print(
                "Upload interrupted."
            )

            print(
                "The upload session remains in SQLite."
            )

            print(
                "Run the same command again "
                "to continue."
            )

            update_upload_status = """
                                   UPDATE videos
                                   SET
                                       youtube_status = 'paused',
                                       updated_at = datetime('now')
                                   WHERE id = ? \
                                   """

            conn.execute(
                update_upload_status,
                (video_id,)
            )

            conn.commit()

            return

        except Exception as e:
            mark_failed(
                conn,
                video_id,
                str(e)
            )

            raise

        # ----------------------------------------------------
        # Completed
        # ----------------------------------------------------

        mark_completed(
            conn,
            video_id,
            youtube_id
        )

        print()
        print(
            "=" * 70
        )

        print(
            "UPLOAD COMPLETED"
        )

        print(
            f"YouTube ID : {youtube_id}"
        )

        print(
            "YouTube URL: "
            f"https://www.youtube.com/watch?v="
            f"{youtube_id}"
        )

        print(
            "Privacy    : PRIVATE"
        )

        print(
            "=" * 70
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()