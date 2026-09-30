import re


def get_value(row, key, default=""):
    """
    Works with sqlite3.Row and normal dict.
    """
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default

    return default if value is None else value


def build_title(match, period):
    home = (
            get_value(match, "home_team_title")
            or get_value(match, "home_team_name")
    )

    away = (
            get_value(match, "away_team_title")
            or get_value(match, "away_team_name")
    )

    match_date = get_value(match, "match_date")

    score = ""

    home_score = get_value(match, "home_score", None)
    away_score = get_value(match, "away_score", None)

    if home_score is not None and away_score is not None:
        score = f" | {home_score}-{away_score}"

    return (
        f"{match_date} | "
        f"{home} vs {away}"
        f"{score} | {period}"
    )


def build_description(
        match,
        game_id,
        period,
        filename,
        sha256,
):
    home = (
            get_value(match, "home_team_title")
            or get_value(match, "home_team_name")
    )

    away = (
            get_value(match, "away_team_title")
            or get_value(match, "away_team_name")
    )

    home_score = get_value(match, "home_score", None)
    away_score = get_value(match, "away_score", None)

    score = ""

    if home_score is not None and away_score is not None:
        score = f"{home_score}-{away_score}"

    match_date = get_value(match, "match_date")
    division_title = get_value(match, "division_title")

    return f"""Soccer Video Backup

Game: {game_id}
Date: {match_date}
Match: {home} vs {away}
Score: {score}
Period: {period}
Competition: {division_title}

File: {filename}
SHA256: {sha256}
Source: Trace
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

    fields = [
        "home_team_title",
        "home_team_abbr",
        "away_team_title",
        "away_team_abbr",
        "division_title",
        "match_date",
    ]

    for key in fields:
        value = get_value(match, key)

        if value:
            tags.append(str(value))

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


def extract_backup_metadata(description):
    if not description:
        return {}

    result = {}

    patterns = {
        "game_id": r"^Game:\s*(.+)$",
        "match_date": r"^Date:\s*(.+)$",
        "match": r"^Match:\s*(.+)$",
        "score": r"^Score:\s*(.+)$",
        "period": r"^Period:\s*(.+)$",
        "competition": r"^Competition:\s*(.+)$",
        "original_filename": r"^File:\s*(.+)$",
        "sha256": r"^SHA256:\s*([a-fA-F0-9]{64})$",
        "source": r"^Source:\s*(.+)$",
    }

    for line in description.splitlines():
        line = line.strip()

        for key, pattern in patterns.items():
            match = re.match(pattern, line)

            if match:
                result[key] = match.group(1).strip()
                break

    return result