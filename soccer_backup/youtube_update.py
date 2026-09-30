import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from youtube_metadata import (
    build_title,
    build_description,
    build_tags,
)


DB_FILE = "soccer_backup.db"
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


def get_youtube():
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build(
        "youtube",
        "v3",
        credentials=creds
    )


def format_date(full_date):
    if not full_date:
        return ""

    try:
        dt = datetime.fromisoformat(
            full_date.replace("Z", "+00:00")
        )
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return full_date[:10]


def team_display(title, abbr):
    if title and abbr:
        return f"{title} ({abbr})"

    return title or abbr or ""



def load_videos(conn, game_id=None, video_id=None):
    query = """
            SELECT
                v.id,
                v.game_id,
                v.original_filename,
                v.original_path,
                v.period,
                v.sha256,
                v.youtube_id,

                m.full_date,
                m.match_date,
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

            WHERE v.youtube_id IS NOT NULL
              AND v.youtube_id != '' \
            """

    params = []

    if game_id is not None:
        query += """
          AND v.game_id = ?
        """
        params.append(game_id)

    if video_id is not None:
        query += """
          AND v.id = ?
        """
        params.append(video_id)

    query += """
        ORDER BY v.period
    """

    return conn.execute(
        query,
        params
    ).fetchall()



def get_current_video(youtube, youtube_id):
    response = (
        youtube.videos()
        .list(
            part="snippet,status",
            id=youtube_id
        )
        .execute()
    )

    items = response.get("items", [])

    if not items:
        return None

    return items[0]


def update_video(
        youtube,
        youtube_id,
        title,
        description,
        tags
):
    current = get_current_video(
        youtube,
        youtube_id
    )

    if current is None:
        print(
            f"ERROR: YouTube video not found: "
            f"{youtube_id}"
        )
        return False

    current_snippet = current["snippet"]

    category_id = current_snippet.get(
        "categoryId",
        "17"
    )

    body = {
        "id": youtube_id,
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id
        }
    }

    (
        youtube.videos()
        .update(
            part="snippet",
            body=body
        )
        .execute()
    )

    return True


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Update YouTube metadata "
            "from soccer_backup.db"
        )
    )

    parser.add_argument(
        "--db",
        default=DB_FILE,
        help=f"SQLite database "
             f"(default: {DB_FILE})"
    )

    parser.add_argument(
        "--game-id",
        type=int,
        help=(
            "Update all YouTube videos "
            "for this Trace Game ID"
        )
    )

    parser.add_argument(
        "--video-id",
        type=int,
        help=(
            "Update one SQLite videos.id"
        )
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Update all videos "
            "with youtube_id"
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show generated metadata "
            "without updating YouTube"
        )
    )

    args = parser.parse_args()

    if not (
            args.all
            or args.game_id is not None
            or args.video_id is not None
    ):
        parser.error(
            "Specify --all, --game-id, "
            "or --video-id"
        )

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        rows = load_videos(
            conn,
            game_id=args.game_id,
            video_id=args.video_id
        )

        print("DEBUG columns:", rows[0].keys() if rows else "NO ROWS")

        if not rows:
            print(
                "No YouTube videos found."
            )
            return

        youtube = None

        if not args.dry_run:
            youtube = get_youtube()

        for row in rows:

            match = {
                "game_id": row["game_id"],
                "full_date": row["full_date"],
                "division_title":
                    row["division_title"],

                "home_team_title":
                    row["home_team_title"],

                "home_team_abbr":
                    row["home_team_abbr"],

                "home_score":
                    row["home_score"],

                "away_team_title":
                    row["away_team_title"],

                "away_team_abbr":
                    row["away_team_abbr"],

                "away_score":
                    row["away_score"],
                "sha256": row["sha256"],
            }

            title = build_title(
                match,
                row["period"]
            )


            description = build_description(
                match,
                row["game_id"],
                row["period"],
                row["original_filename"],
                row["sha256"],
            )

            tags = build_tags(
                match,
                row["game_id"],
                row["period"],
            )

            print()
            print("=" * 70)

            print(
                f"SQLite video : {row['id']}"
            )

            print(
                f"Game ID      : {row['game_id']}"
            )

            print(
                f"YouTube ID   : {row['youtube_id']}"
            )

            print(
                f"File         : "
                f"{row['original_filename']}"
            )

            print()
            print("TITLE:")
            print(title)

            print()
            print("TAGS:")
            print(", ".join(tags))

            print()
            print("DESCRIPTION:")
            print(description)

            if args.dry_run:
                print()
                print(
                    "DRY RUN - "
                    "not updating YouTube."
                )
                continue

            print()
            print("Updating YouTube...")

            success = update_video(
                youtube,
                row["youtube_id"],
                title,
                description,
                tags
            )

            if success:
                print(
                    "UPDATED successfully."
                )

        print()
        print("=" * 70)
        print("Done.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()