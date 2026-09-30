import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = "soccer_backup.db"


SCHEMA = """
         CREATE TABLE IF NOT EXISTS matches (
                                                game_id INTEGER PRIMARY KEY,

                                                full_date TEXT,
                                                match_date TEXT,

                                                sport_type TEXT,

                                                division_id INTEGER,
                                                division_title TEXT,

                                                approx_half_duration INTEGER,
                                                churned INTEGER,
                                                is_multicam INTEGER,
                                                num_equip INTEGER,
                                                num_subs INTEGER,
                                                locked INTEGER,
                                                video_render_type TEXT,
                                                status TEXT,

                                                home_team_id INTEGER,
                                                home_team_name TEXT,
                                                home_team_title TEXT,
                                                home_team_abbr TEXT,
                                                home_score INTEGER,

                                                away_team_id INTEGER,
                                                away_team_name TEXT,
                                                away_team_title TEXT,
                                                away_team_abbr TEXT,
                                                away_score INTEGER,

                                                trace_base_path TEXT,

                                                trace_json TEXT NOT NULL,

                                                created_at TEXT NOT NULL,
                                                updated_at TEXT NOT NULL
         );


         CREATE TABLE IF NOT EXISTS videos (
                                               id INTEGER PRIMARY KEY AUTOINCREMENT,

                                               game_id INTEGER NOT NULL,

                                               original_filename TEXT NOT NULL,
                                               original_path TEXT,

                                               period TEXT,

                                               file_size INTEGER,
                                               sha256 TEXT UNIQUE,

                                               youtube_id TEXT,
                                               youtube_status TEXT DEFAULT 'pending',

                                               created_at TEXT NOT NULL,
                                               updated_at TEXT NOT NULL,

                                               FOREIGN KEY (game_id)
             REFERENCES matches(game_id)
             );


         CREATE INDEX IF NOT EXISTS idx_videos_game_id
             ON videos(game_id);


         CREATE INDEX IF NOT EXISTS idx_videos_sha256
             ON videos(sha256); \
         """


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def parse_period(filename):
    """
    Trace-FullGame-20260926-period-1.mov
                         ^^^^^^^^^^
                         download date ignored

    period-1 -> 1H
    period-2 -> 2H
    """

    match = re.search(
        r"(?:^|[-_])period[-_]?([12])(?:[-_.]|$)",
        filename,
        re.IGNORECASE
    )

    if not match:
        return None

    return f"{match.group(1)}H"


def load_trace_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both:
    #
    # {
    #   "data": {
    #       "teamGames": [...]
    #   }
    # }
    #
    # and:
    #
    # {
    #   "0": {...},
    #   "1": {...}
    # }

    if "data" in data:
        games = data["data"].get("teamGames")

        if games is None:
            raise ValueError(
                "JSON does not contain data.teamGames"
            )

        return games

    # Old format
    games = []

    for value in data.values():
        if isinstance(value, dict) and "game_id" in value:
            games.append(value)

    if not games:
        raise ValueError(
            "Could not find any games in Trace JSON"
        )

    return games


def find_game(games, game_id):
    for game in games:
        if int(game.get("game_id", -1)) == int(game_id):
            return game

    return None


def parse_match_date(full_date):
    if not full_date:
        return None

    dt = datetime.fromisoformat(
        full_date.replace("Z", "+00:00")
    )

    return dt.date().isoformat()


def upsert_match(conn, game):
    game_id = int(game["game_id"])

    home = game.get("home_team") or {}
    away = game.get("away_team") or {}

    timestamp = now()

    conn.execute(
        """
        INSERT INTO matches (
            game_id,

            full_date,
            match_date,

            sport_type,

            division_id,
            division_title,

            approx_half_duration,
            churned,
            is_multicam,
            num_equip,
            num_subs,
            locked,
            video_render_type,
            status,

            home_team_id,
            home_team_name,
            home_team_title,
            home_team_abbr,
            home_score,

            away_team_id,
            away_team_name,
            away_team_title,
            away_team_abbr,
            away_score,

            trace_base_path,
            trace_json,

            created_at,
            updated_at
        )
        VALUES (
                   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   ?, ?, ?, ?
               )

            ON CONFLICT(game_id)
        DO UPDATE SET

            full_date = excluded.full_date,
                           match_date = excluded.match_date,

                           sport_type = excluded.sport_type,

                           division_id = excluded.division_id,
                           division_title = excluded.division_title,

                           approx_half_duration =
                           excluded.approx_half_duration,

                           churned = excluded.churned,
                           is_multicam = excluded.is_multicam,
                           num_equip = excluded.num_equip,
                           num_subs = excluded.num_subs,
                           locked = excluded.locked,

                           video_render_type =
                           excluded.video_render_type,

                           status = excluded.status,

                           home_team_id = excluded.home_team_id,
                           home_team_name = excluded.home_team_name,
                           home_team_title = excluded.home_team_title,
                           home_team_abbr = excluded.home_team_abbr,
                           home_score = excluded.home_score,

                           away_team_id = excluded.away_team_id,
                           away_team_name = excluded.away_team_name,
                           away_team_title = excluded.away_team_title,
                           away_team_abbr = excluded.away_team_abbr,
                           away_score = excluded.away_score,

                           trace_base_path = excluded.trace_base_path,
                           trace_json = excluded.trace_json,

                           updated_at = excluded.updated_at
        """,
        (
            game_id,

            game.get("full_date"),
            parse_match_date(game.get("full_date")),

            game.get("sport_type"),

            game.get("division_id"),
            game.get("division_title"),

            game.get("approx_half_duration"),

            int(bool(game.get("churned"))),
            int(bool(game.get("is_multicam"))),

            game.get("num_equip"),
            game.get("num_subs"),

            int(bool(game.get("locked"))),

            game.get("video_render_type"),
            game.get("status"),

            home.get("team_id"),
            home.get("name"),
            home.get("title"),
            home.get("abbr"),
            home.get("score"),

            away.get("team_id"),
            away.get("name"),
            away.get("title"),
            away.get("abbr"),
            away.get("score"),

            game.get("base_path"),

            json.dumps(
                game,
                ensure_ascii=False
            ),

            timestamp,
            timestamp
        )
    )


def insert_video(
        conn,
        filename,
        filepath,
        game_id,
        period,
        sha256,
        file_size
):
    timestamp = now()

    existing = conn.execute(
        """
        SELECT
            id,
            game_id,
            original_filename
        FROM videos
        WHERE sha256 = ?
        """,
        (sha256,)
    ).fetchone()

    if existing:
        print()
        print("DUPLICATE FILE")
        print(f"Video ID : {existing[0]}")
        print(f"Game ID  : {existing[1]}")
        print(f"Filename : {existing[2]}")
        return False

    conn.execute(
        """
        INSERT INTO videos (
            game_id,
            original_filename,
            original_path,
            period,
            file_size,
            sha256,
            youtube_status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            game_id,
            filename,
            filepath,
            period,
            file_size,
            sha256,
            timestamp,
            timestamp
        )
    )

    return True


def print_match(game, filename, period):
    home = game.get("home_team") or {}
    away = game.get("away_team") or {}

    print()
    print("=" * 70)

    print(f"File     : {filename}")
    print(f"Period   : {period or 'UNKNOWN'}")
    print(f"Game ID  : {game['game_id']}")

    print(f"Date     : {game.get('full_date')}")

    print(
        f"Match    : "
        f"{home.get('title')} "
        f"{home.get('score')} - "
        f"{away.get('score')} "
        f"{away.get('title')}"
    )

    print(
        f"Division : "
        f"{game.get('division_title')}"
    )

    print(
        f"Duration : "
        f"{game.get('approx_half_duration')} sec"
    )

    print(
        f"Status   : "
        f"{game.get('status')}"
    )

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Associate a local Trace video filename "
            "with a Trace Game ID and import metadata into SQLite."
        )
    )

    parser.add_argument(
        "filename",
        help="Video filename or full path"
    )

    parser.add_argument(
        "game_id",
        type=int,
        help="Trace Game ID"
    )

    parser.add_argument(
        "--trace-json",
        required=True,
        help="Trace teamGames JSON file"
    )

    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help=f"SQLite DB (default: {DEFAULT_DB})"
    )

    args = parser.parse_args()

    video_path = Path(args.filename)

    filename = video_path.name

    trace_json_path = Path(args.trace_json)

    if not trace_json_path.is_file():
        raise SystemExit(
            f"ERROR: Trace JSON not found: "
            f"{trace_json_path}"
        )

    games = load_trace_json(trace_json_path)

    game = find_game(
        games,
        args.game_id
    )

    if game is None:
        raise SystemExit(
            f"ERROR: Game ID {args.game_id} "
            f"not found in Trace JSON."
        )

    period = parse_period(filename)

    print_match(
        game,
        filename,
        period
    )

    conn = sqlite3.connect(args.db)

    try:
        conn.executescript(SCHEMA)

        upsert_match(
            conn,
            game
        )

        # If full local path exists, calculate SHA256.
        # If only a filename was supplied, leave file hash NULL.
        if video_path.is_file():
            print()
            print("Calculating SHA256...")
            sha256 = sha256_file(video_path)

            file_size = video_path.stat().st_size
            original_path = str(video_path.resolve())

            print(f"SHA256  : {sha256}")
            print(f"Size    : {file_size:,} bytes")

        else:
            print()
            print(
                "WARNING: local file not found."
            )
            print(
                "Metadata will still be imported; "
                "SHA256/path will be NULL."
            )

            sha256 = None
            file_size = None
            original_path = str(video_path)

        inserted = insert_video(
            conn,
            filename=filename,
            filepath=original_path,
            game_id=args.game_id,
            period=period,
            sha256=sha256,
            file_size=file_size
        )

        conn.commit()

        if inserted:
            print()
            print("Imported successfully.")
        else:
            print()
            print("Nothing changed.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()