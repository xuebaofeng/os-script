import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


DB_FILE = "soccer_backup.db"
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
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


def build_title(match, video):
    home = team_display(
        match["home_team_title"],
        match["home_team_abbr"]
    )

    away = team_display(
        match["away_team_title"],
        match["away_team_abbr"]
    )

    date = format_date(match["full_date"])

    score = ""

    if (
            match["home_score"] is not None
            and match["away_score"] is not None
    ):
        score = (
            f"{match['home_score']}-"
            f"{match['away_score']}"
        )

    parts = [
        home,
        "vs",
        away
    ]

    if date:
        parts.append(date)

    if score:
        parts.append(score)

    if video["period"]:
        parts.append(video["period"])

    return " | ".join(parts)


def build_description(match, video):
    home = team_display(
        match["home_team_title"],
        match["home_team_abbr"]
    )

    away = team_display(
        match["away_team_title"],
        match["away_team_abbr"]
    )

    date = format_date(match["full_date"])

    division = match["division_title"] or ""

    score = ""

    if (
            match["home_score"] is not None
            and match["away_score"] is not None
    ):
        score = (
            f"{match['home_score']}-"
            f"{match['away_score']}"
        )

    lines = [
        "Youth Soccer Match Video",
        "",
        f"Match Date: {date}",
        f"Match: {home} vs {away}",
    ]

    if score:
        lines.append(
            f"Score: {score}"
        )

    if video["period"]:
        lines.append(
            f"Period: {video['period']}"
        )

    if division:
        lines.append(
            f"Competition: {division}"
        )

    lines.extend([
        "",
        f"Trace Game ID: {match['game_id']}",
        "Source: Trace",
        "",
        "This video is archived for personal "
        "soccer video backup and analysis."
    ])

    return "\n".join(lines)


def build_tags(match, video):
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

    date = format_date(match["full_date"])

    add(date)

    if video["period"]:
        add(video["period"])

    return tags


def load_videos(conn, game_id=None, video_id=None):
    query = """
            SELECT
                v.id,
                v.game_id,
                v.original_filename,
                v.original_path,
                v.period,
                v.youtube_id,

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

            WHERE v.youtube_id IS NOT NULL
              AND v.youtube_id != '' \
            """

    params = []

    if game_id is not None:
        query += " AND v.game_id = ?"
        params.append(game_id)

    if video_id is not None:
        query += " AND v.id = ?"
        params.append(video_id)

    query += """
        ORDER BY
            m.full_date,
            v.game_id,
            v.period
    """

    return conn.execute(
        query,
        params
    ).fetchall()


def row_to_dict(row):
    return {
        "id": row[0],
        "game_id": row[1],
        "original_filename": row[2],
        "original_path": row[3],
        "period": row[4],
        "youtube_id": row[5],

        "full_date": row[6],
        "division_title": row[7],

        "home_team_title": row[8],
        "home_team_abbr": row[9],
        "home_score": row[10],

        "away_team_title": row[11],
        "away_team_abbr": row[12],
        "away_score": row[13],
    }


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

    try:
        rows = load_videos(
            conn,
            game_id=args.game_id,
            video_id=args.video_id
        )

        if not rows:
            print(
                "No YouTube videos found."
            )
            return

        youtube = None

        if not args.dry_run:
            youtube = get_youtube()

        for row in rows:
            video = row_to_dict(row)

            match = {
                "game_id": video["game_id"],
                "full_date": video["full_date"],
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
                    video["away_score"],
            }

            title = build_title(
                match,
                video
            )

            description = build_description(
                match,
                video
            )

            tags = build_tags(
                match,
                video
            )

            print()
            print("=" * 70)

            print(
                f"SQLite video : {video['id']}"
            )

            print(
                f"Game ID      : {video['game_id']}"
            )

            print(
                f"YouTube ID   : {video['youtube_id']}"
            )

            print(
                f"File         : "
                f"{video['original_filename']}"
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
                video["youtube_id"],
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