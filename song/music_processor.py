
import re
import time
import logging
import argparse
import requests
import threading
import json
import os
import subprocess
import uuid
import sqlite3
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

from pathlib import Path
from difflib import SequenceMatcher
from mutagen import File
from mutagen.id3 import ID3, USLT, SYLT
from mutagen.mp4 import MP4

# ==================== 配置 ====================

MUSIC_ROOT = Path(r"C:\shared\media\CloudMusic")

API = "https://lrclib.net"

SUPPORTED = {
    ".mp3",
    ".m4a",
    ".flac",
    ".opus",
    ".ogg"
}

REQUEST_INTERVAL = 1.0
DEFAULT_WORKERS = 10
NORMALIZE_EXTENSIONS = {".mp3", ".opus"}
TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0
LOUDNESS_TOLERANCE = 1.0
TRUE_PEAK_TOLERANCE = 0.5
LRA_TOLERANCE = 1.0
NEGATIVE_LYRICS_CACHE_SECONDS = 30 * 24 * 60 * 60
SCAN_DB_PATH = MUSIC_ROOT / ".music_processor.db"
LEGACY_SCAN_STATE_PATH = MUSIC_ROOT / ".music_processor_scan.json"
PROFANITY_PATTERNS = (
    re.compile(
        r"操你妈的|去他妈的|操你妈|他妈的|你妈的|傻逼|王八蛋|"
        r"狗屎|混蛋|我操|我草|卧槽|操你|妈的",
        re.IGNORECASE
    ),
    re.compile(
        r"(?<!\w)(?:motherfuck(?:er|ers|ing|ed|s)?|"
        r"fuck(?:s|ed|ing)?|shit(?:ty|s)?|bitch(?:es)?|"
        r"assholes?|bastards?|damn(?:ed|ing)?|hell|crap|"
        r"dicks?|piss(?:ed|ing)?)(?!\w)",
        re.IGNORECASE
    )
)

# ==================== 日志 ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            MUSIC_ROOT / "lyrics.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

_thread_local = threading.local()
_request_lock = threading.Lock()
_process_lock = threading.Lock()
_active_processes = set()
_stop_event = threading.Event()
_next_request_at = 0.0
_lyrics_db_lock = threading.Lock()
_volume_check_successes = set()
_volume_success_lock = threading.Lock()


def open_scan_db():
    connection = sqlite3.connect(SCAN_DB_PATH, timeout=30)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS scan_results (
            path TEXT PRIMARY KEY,
            mtime_ns INTEGER NOT NULL,
            volume_mtime_ns INTEGER,
            volume_checked_at REAL,
            lyrics_checked_at REAL,
            result TEXT
        )
    """)
    scan_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(scan_results)")
    }
    if "volume_mtime_ns" not in scan_columns:
        connection.execute(
            "ALTER TABLE scan_results ADD COLUMN volume_mtime_ns INTEGER"
        )
    connection.execute("""
        CREATE TABLE IF NOT EXISTS lyrics_cache (
            artist_key TEXT NOT NULL,
            title_key TEXT NOT NULL,
            artist TEXT NOT NULL,
            title TEXT NOT NULL,
            plain_lyrics TEXT,
            synced_lyrics TEXT,
            checked_at REAL NOT NULL,
            found INTEGER NOT NULL,
            PRIMARY KEY (artist_key, title_key)
        )
    """)
    connection.commit()

    if LEGACY_SCAN_STATE_PATH.is_file():
        try:
            with LEGACY_SCAN_STATE_PATH.open("r", encoding="utf-8") as state_file:
                legacy_state = json.load(state_file)
            for path, entry in legacy_state.items():
                connection.execute("""
                    INSERT OR IGNORE INTO scan_results (
                        path, mtime_ns, volume_checked_at,
                        lyrics_checked_at, result
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    path,
                    entry.get("mtime_ns"),
                    entry.get("volume_checked_at"),
                    entry.get("lyrics_checked_at"),
                    entry.get("result")
                ))
            connection.commit()
            logger.info("已将旧 JSON 扫描记录导入 SQLite")
        except (
            OSError,
            json.JSONDecodeError,
            AttributeError,
            TypeError,
            sqlite3.Error
        ):
            connection.rollback()
            logger.exception("导入旧 JSON 扫描记录失败")

    return connection


def load_scan_state(connection):
    return {
        row[0]: {
            "mtime_ns": row[1],
            "volume_mtime_ns": row[2],
            "volume_checked_at": row[3],
            "lyrics_checked_at": row[4],
            "result": row[5]
        }
        for row in connection.execute(
            "SELECT path, mtime_ns, volume_mtime_ns, volume_checked_at, "
            "lyrics_checked_at, result "
            "FROM scan_results"
        )
    }


def save_scan_result(connection, path, entry):
    connection.execute("""
        INSERT INTO scan_results (
            path, mtime_ns, volume_mtime_ns, volume_checked_at,
            lyrics_checked_at, result
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            mtime_ns=excluded.mtime_ns,
            volume_mtime_ns=excluded.volume_mtime_ns,
            volume_checked_at=excluded.volume_checked_at,
            lyrics_checked_at=excluded.lyrics_checked_at,
            result=excluded.result
    """, (
        path,
        entry["mtime_ns"],
        entry.get("volume_mtime_ns"),
        entry.get("volume_checked_at"),
        entry.get("lyrics_checked_at"),
        entry.get("result")
    ))
    connection.commit()


def lyrics_cache_key(meta):
    return meta["artist"].strip().casefold(), meta["title"].strip().casefold()


def load_cached_lyrics(meta):
    artist_key, title_key = lyrics_cache_key(meta)
    with _lyrics_db_lock:
        connection = sqlite3.connect(SCAN_DB_PATH, timeout=30)
        try:
            row = connection.execute("""
                SELECT plain_lyrics, synced_lyrics, checked_at, found
                FROM lyrics_cache
                WHERE artist_key=? AND title_key=?
            """, (artist_key, title_key)).fetchone()
        finally:
            connection.close()

    if not row:
        return False, None
    age = time.time() - row[2]
    if not row[3]:
        if 0 <= age < NEGATIVE_LYRICS_CACHE_SECONDS:
            return True, None
        return False, None
    return True, {
        "plainLyrics": row[0] or "",
        "syncedLyrics": row[1] or ""
    }


def save_cached_lyrics(meta, data):
    artist_key, title_key = lyrics_cache_key(meta)
    found = bool(data and (data.get("plainLyrics") or data.get("syncedLyrics")))
    with _lyrics_db_lock:
        connection = sqlite3.connect(SCAN_DB_PATH, timeout=30)
        try:
            connection.execute("""
                INSERT INTO lyrics_cache (
                    artist_key, title_key, artist, title, plain_lyrics,
                    synced_lyrics, checked_at, found
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artist_key, title_key) DO UPDATE SET
                    artist=excluded.artist,
                    title=excluded.title,
                    plain_lyrics=excluded.plain_lyrics,
                    synced_lyrics=excluded.synced_lyrics,
                    checked_at=excluded.checked_at,
                    found=excluded.found
            """, (
                artist_key,
                title_key,
                meta["artist"],
                meta["title"],
                (data.get("plainLyrics") or "") if found else "",
                (data.get("syncedLyrics") or "") if found else "",
                time.time(),
                int(found)
            ))
            connection.commit()
        finally:
            connection.close()


def relative_key(path):
    return str(path.relative_to(MUSIC_ROOT))


def lyrics_already_present(entry, mtime_ns):
    if not entry or entry.get("mtime_ns") != mtime_ns:
        return False
    return entry.get("result") in {"success", "skipped"}


def get_session():
    """Return a requests session dedicated to the current worker thread."""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
        _thread_local.session.headers.update({
            "User-Agent": "LocalLyricsEmbedder/1.0"
        })
    return _thread_local.session


def rate_limited_get(url, **kwargs):
    """Space out API request starts while allowing requests to overlap."""
    global _next_request_at
    with _request_lock:
        delay = _next_request_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _next_request_at = time.monotonic() + REQUEST_INTERVAL
    return get_session().get(url, **kwargs)


def run_ffmpeg(command):
    """Run FFmpeg while allowing Ctrl+C in the main thread to stop it."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )
    with _process_lock:
        _active_processes.add(process)
    try:
        _, stderr = process.communicate()
        return process.returncode, stderr
    finally:
        with _process_lock:
            _active_processes.discard(process)


def stop_active_ffmpeg():
    with _process_lock:
        processes = list(_active_processes)
    for process in processes:
        if process.poll() is None:
            process.terminate()


def analyze_loudness(path):
    command = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-map", "0:a:0", "-vn", "-sn", "-dn",
        "-af",
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        "-f", "null", "-"
    ]
    return_code, stderr = run_ffmpeg(command)
    output = stderr.decode("utf-8", errors="ignore")
    if return_code != 0:
        raise RuntimeError(
            f"FFmpeg 响度分析失败（退出码 {return_code}）：\n{output[-3000:]}"
        )

    required_fields = {
        "input_i",
        "input_tp",
        "input_lra",
        "input_thresh",
        "target_offset"
    }
    decoder = json.JSONDecoder()
    for match in reversed(list(re.finditer(r"\{", output))):
        try:
            report, _ = decoder.raw_decode(output[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(report, dict) and required_fields.issubset(report):
            return report

    raise RuntimeError(
        "FFmpeg 未生成有效的 loudnorm 测量报告：\n"
        f"{output[-3000:]}"
    )


def normalize_audio(path):
    """Two-pass loudness normalization from norm.py, using a sibling temp file."""
    if path.suffix.lower() not in NORMALIZE_EXTENSIONS:
        logger.info("跳过不支持响度标准化的格式：%s", path.name)
        return

    measurements = analyze_loudness(path)
    try:
        measured_i = float(measurements["input_i"])
        measured_tp = float(measurements["input_tp"])
        measured_lra = float(measurements["input_lra"])
    except (KeyError, TypeError, ValueError):
        measured_i = measured_tp = measured_lra = float("nan")

    if (
        abs(measured_i - TARGET_I) <= LOUDNESS_TOLERANCE
        and measured_tp <= TARGET_TP + TRUE_PEAK_TOLERANCE
        and measured_lra <= TARGET_LRA + LRA_TOLERANCE
    ):
        logger.info(
            "已符合响度标准，跳过重编码：%s (I=%s, TP=%s, LRA=%s)",
            path.name,
            measurements.get("input_i"),
            measurements.get("input_tp"),
            measurements.get("input_lra")
        )
        return

    filter_value = (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
        f"measured_I={measurements['input_i']}:"
        f"measured_TP={measurements['input_tp']}:"
        f"measured_LRA={measurements['input_lra']}:"
        f"measured_thresh={measurements['input_thresh']}:"
        f"offset={measurements['target_offset']}:linear=true"
    )
    temporary_path = path.with_name(
        f"{path.stem}.{uuid.uuid4().hex}.tmp{path.suffix}"
    )
    codec_args = (
        ["-c:a", "libmp3lame", "-b:a", "192k"]
        if path.suffix.lower() == ".mp3"
        else ["-c:a", "libopus", "-b:a", "128k"]
    )
    command = [
        "ffmpeg", "-y", "-hide_banner", "-i", str(path),
        "-map", "0:a:0", "-vn", "-sn", "-dn",
        "-map_metadata", "0", "-af", filter_value,
        *codec_args, str(temporary_path)
    ]

    try:
        lyric_snapshot = capture_lyrics_tags(path)
        return_code, stderr = run_ffmpeg(command)
        if return_code != 0:
            output = stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg 响度标准化失败：{output[-1000:]}")

        # Restore lyric frames to the temporary output before replacing the
        # source. If restoration fails, the original audio remains untouched.
        restore_lyrics_tags(temporary_path, lyric_snapshot)

        for attempt in range(5):
            try:
                os.replace(temporary_path, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.5 * (attempt + 1))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    logger.info("完成响度标准化：%s", path.name)


def capture_lyrics_tags(path):
    audio = File(path, easy=False)
    if audio is None or audio.tags is None:
        return None

    if path.suffix.lower() == ".mp3":
        frames = audio.tags.getall("USLT") + audio.tags.getall("SYLT")
        return {"id3_frames": copy.deepcopy(frames)} if frames else None

    keys = ("\xa9lyr",) if path.suffix.lower() == ".m4a" else (
        "LYRICS", "UNSYNCEDLYRICS"
    )
    values = {
        key: copy.deepcopy(audio.tags[key])
        for key in keys
        if key in audio.tags
    }
    return {"values": values} if values else None


def restore_lyrics_tags(path, snapshot):
    if not snapshot:
        return

    if path.suffix.lower() == ".mp3":
        tags = ID3(path)
        tags.delall("USLT")
        tags.delall("SYLT")
        for frame in snapshot.get("id3_frames", []):
            tags.add(frame)
        tags.save(path, v2_version=3)
        return

    audio = File(path, easy=False)
    if audio is None:
        raise RuntimeError(f"无法打开标准化后的文件以恢复歌词：{path}")
    if audio.tags is None:
        audio.add_tags()
    for key, value in snapshot.get("values", {}).items():
        audio.tags[key] = value
    audio.save()

# ==================== 基础处理 ====================

def clean(value):
    if not value:
        return ""

    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""

    return str(value).strip()


def parse_filename(path):
    """
    支持：
    Artist - Title.opus
    Artist-Title.mp3
    """

    name = path.stem

    if " - " in name:
        artist, title = name.split(" - ", 1)
        return artist.strip(), title.strip()

    if "-" in name:
        artist, title = name.split("-", 1)
        return artist.strip(), title.strip()

    return "", name.strip()


def get_metadata(path):
    audio = File(path, easy=True)

    if audio is None:
        return None

    tags = audio.tags or {}

    artist = clean(tags.get("artist"))
    title = clean(tags.get("title"))
    album = clean(tags.get("album"))

    file_artist, file_title = parse_filename(path)

    artist = artist or file_artist
    title = title or file_title

    duration = None

    if audio.info and audio.info.length:
        duration = int(round(audio.info.length))

    return {
        "artist": artist,
        "title": title,
        "album": album,
        "duration": duration
    }


# ==================== 歌词查询 ====================

def get_lyrics(meta, use_cache=True):

    if use_cache:
        cached, cached_data = load_cached_lyrics(meta)
        if cached:
            if cached_data is None:
                logger.info(
                    "数据库记录云端暂无歌词，30 天内跳过查询：%s - %s",
                    meta["artist"],
                    meta["title"]
                )
            else:
                logger.info(
                    "使用数据库歌词缓存：%s - %s",
                    meta["artist"],
                    meta["title"]
                )
            return cached_data

    params = {
        "artist_name": meta["artist"],
        "track_name": meta["title"]
    }

    if meta["album"]:
        params["album_name"] = meta["album"]

    if meta["duration"]:
        params["duration"] = meta["duration"]

    # First try the exact lookup. Network and server errors propagate so
    # transient failures are not stored as a 30-day "no lyrics" result.
    response = rate_limited_get(
        f"{API}/api/get",
        params=params,
        timeout=20
    )

    data = None
    if response.status_code == 200:
        exact = response.json()
        if not exact.get("instrumental") and (
            exact.get("plainLyrics") or exact.get("syncedLyrics")
        ):
            data = exact
    elif response.status_code != 404:
        response.raise_for_status()

    if data is None:
        response = rate_limited_get(
            f"{API}/api/search",
            params={
                "track_name": meta["title"],
                "artist_name": meta["artist"]
            },
            timeout=20
        )
        response.raise_for_status()
        candidates = response.json()

        for item in candidates:
            if item.get("instrumental"):
                continue

            title_score = SequenceMatcher(
                None,
                meta["title"].lower(),
                (item.get("trackName") or "").lower()
            ).ratio()
            artist_score = SequenceMatcher(
                None,
                meta["artist"].lower(),
                (item.get("artistName") or "").lower()
            ).ratio()

            if title_score < 0.95 or artist_score < 0.90:
                continue
            if meta["duration"] and item.get("duration") and abs(
                meta["duration"] - item["duration"]
            ) > 5:
                continue
            if item.get("plainLyrics") or item.get("syncedLyrics"):
                data = item
                break

    save_cached_lyrics(meta, data)
    return data


def find_lyric_profanity(lyrics):
    """Return unique profanity terms found in lyric text."""
    found = set()
    for pattern in PROFANITY_PATTERNS:
        found.update(match.group(0) for match in pattern.finditer(lyrics))
    return sorted(found, key=str.casefold)


def log_lyric_profanity(path, lyrics):
    terms = find_lyric_profanity(lyrics)
    if terms:
        logger.warning(
            "歌词检测到疑似脏话（%s）：%s",
            "、".join(terms),
            path
        )


# ==================== 已有歌词检查 ====================

def has_existing_lyrics(path):

    audio = File(path, easy=False)

    if audio is None or audio.tags is None:
        return False

    tags = audio.tags

    ext = path.suffix.lower()

    if ext == ".mp3":

        for key in tags.keys():

            if key.startswith("USLT"):
                return True

            if key.startswith("SYLT"):
                return True

        return False

    if ext == ".m4a":
        return bool(tags.get("\xa9lyr"))

    return bool(
        tags.get("LYRICS")
        or tags.get("UNSYNCEDLYRICS")
    )


# ==================== 嵌入歌词 ====================

def embed_lyrics(path, plain, synced):

    ext = path.suffix.lower()

    if ext == ".mp3":

        tags = ID3(path)

        tags.delall("USLT")
        tags.delall("SYLT")

        if plain:

            tags.add(USLT(
                encoding=3,
                lang="eng",
                desc="Lyrics",
                text=plain
            ))

        if synced:

            timestamps = []

            for line in synced.splitlines():

                match = re.match(
                    r"\[(\d+):(\d+(?:\.\d+)?)\](.*)",
                    line
                )

                if not match:
                    continue

                minutes = int(match.group(1))
                seconds = float(match.group(2))

                timestamp = int(
                    (minutes * 60 + seconds) * 1000
                )

                timestamps.append((
                    match.group(3).strip(),
                    timestamp
                ))

            if timestamps:

                tags.add(SYLT(
                    encoding=3,
                    lang="eng",
                    format=2,
                    type=1,
                    desc="Lyrics",
                    text=timestamps
                ))

        tags.save(path, v2_version=3)

    elif ext == ".m4a":

        audio = MP4(path)

        if audio.tags is None:
            audio.add_tags()

        if plain:
            audio.tags["\xa9lyr"] = plain

        audio.save()

    else:

        audio = File(path)

        if audio.tags is None:
            audio.add_tags()

        if plain:
            audio.tags["LYRICS"] = plain

        audio.save()


def read_embedded_lyrics(path):
    """Read existing lyric tags for storage in the SQLite lyrics cache."""
    audio = File(path, easy=False)
    if audio is None or audio.tags is None:
        return None

    plain = ""
    synced = ""
    if path.suffix.lower() == ".mp3":
        plain_frames = audio.tags.getall("USLT")
        if plain_frames:
            plain = plain_frames[0].text or ""

        lines = []
        for frame in audio.tags.getall("SYLT"):
            for text, timestamp in frame.text:
                minutes, remainder_ms = divmod(int(timestamp), 60_000)
                seconds = remainder_ms / 1000
                lines.append(f"[{minutes:02d}:{seconds:05.2f}]{text}")
        synced = "\n".join(lines)
    elif path.suffix.lower() == ".m4a":
        plain = clean(audio.tags.get("\xa9lyr"))
    else:
        plain = clean(audio.tags.get("LYRICS") or audio.tags.get("UNSYNCEDLYRICS"))

    if not plain and synced:
        plain = re.sub(r"\[\d{1,2}:\d{2}(?:\.\d+)?\]", "", synced).strip()
    if not plain and not synced:
        return None
    return {"plainLyrics": plain, "syncedLyrics": synced}


# ==================== 保存 LRC ====================

# ==================== 单曲处理 ====================

def process_file(path, overwrite=False, normalize=True, check_lyrics=True):

    try:

        if _stop_event.is_set():
            return "skipped"

        if normalize:
            normalize_audio(path)
            with _volume_success_lock:
                _volume_check_successes.add(str(path))

        if _stop_event.is_set():
            return "skipped"

        if not check_lyrics:
            logger.info("歌词检查跳过（此前已有歌词）：%s", path)
            return "skipped"

        if (
            has_existing_lyrics(path)
            and not overwrite
        ):

            existing_meta = get_metadata(path)
            existing_lyrics = None
            if (
                existing_meta
                and existing_meta["artist"]
                and existing_meta["title"]
            ):
                existing_lyrics = read_embedded_lyrics(path)
                if existing_lyrics:
                    log_lyric_profanity(
                        path,
                        "\n".join((
                            existing_lyrics.get("plainLyrics") or "",
                            existing_lyrics.get("syncedLyrics") or ""
                        ))
                    )
                cached, _ = load_cached_lyrics(existing_meta)
                if existing_lyrics and not cached:
                    save_cached_lyrics(existing_meta, existing_lyrics)

            logger.info(
                "跳过已有歌词：%s",
                path.name
            )

            return "skipped"

        meta = get_metadata(path)

        if (
            not meta
            or not meta["artist"]
            or not meta["title"]
        ):

            logger.warning(
                "无法识别歌曲信息：%s",
                path.name
            )

            return "failed"

        logger.info(
            "查询：%s - %s",
            meta["artist"],
            meta["title"]
        )

        data = get_lyrics(meta, use_cache=not overwrite)

        if _stop_event.is_set():
            return "skipped"

        if not data:

            logger.warning(
                "未找到歌词：%s",
                path.name
            )

            return "missing"

        plain = data.get("plainLyrics") or ""
        synced = data.get("syncedLyrics") or ""

        # 同步歌词转换为普通歌词
        if not plain and synced:

            plain = re.sub(
                r"\[\d{1,2}:\d{2}(?:\.\d+)?\]",
                "",
                synced
            ).strip()

        if not plain and not synced:
            return "missing"

        log_lyric_profanity(path, "\n".join((plain, synced)))

        # 嵌入音频
        embed_lyrics(
            path,
            plain,
            synced
        )

        logger.info(
            "完成：%s (%s)",
            path.name,
            "同步歌词" if synced else "普通歌词"
        )

        return "success"

    except Exception:

        logger.exception(
            "处理失败：%s",
            path
        )

        return "failed"


# ==================== 主程序 ====================

def main():

    parser = argparse.ArgumentParser(
        description="批量下载并嵌入音乐歌词"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已有音频歌词"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"并发处理的歌曲数（默认：{DEFAULT_WORKERS}）"
    )

    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers 必须大于 0")

    if not MUSIC_ROOT.is_dir():

        print(
            "曲库目录不存在：",
            MUSIC_ROOT
        )

        return

    # 排除 lyrics 目录
    files = [
        p
        for p in MUSIC_ROOT.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUPPORTED
        and "lyrics" not in p.relative_to(
            MUSIC_ROOT
        ).parts
    ]

    scan_db = open_scan_db()
    scan_state = load_scan_state(scan_db)
    work_items = []
    missing_files = []
    cached_count = 0
    for path in files:
        key = relative_key(path)
        entry = scan_state.get(key, {})
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            logger.exception("无法读取文件修改时间：%s", path)
            work_items.append((path, True, True))
            continue

        volume_pending = entry.get("volume_mtime_ns") != mtime_ns
        lyrics_present = lyrics_already_present(entry, mtime_ns)
        if lyrics_present:
            try:
                existing_lyrics = read_embedded_lyrics(path)
                if existing_lyrics:
                    log_lyric_profanity(
                        path,
                        "\n".join((
                            existing_lyrics.get("plainLyrics") or "",
                            existing_lyrics.get("syncedLyrics") or ""
                        ))
                    )
            except Exception:
                logger.exception("读取歌词用于脏话检测失败：%s", path)

        if lyrics_present and not volume_pending:
            cached_count += 1
            logger.info(
                "整首跳过（文件未修改，已有歌词且音量已检查）：%s",
                path
            )
            continue

        if not volume_pending:
            logger.info("音量检查跳过（文件修改时间未变）：%s", path)
        if lyrics_present:
            logger.info("歌词检查跳过（此前已有歌词）：%s", path)

        # Recheck lyrics after 30 days, but analyze loudness only after a
        # modification time change (or when this file has no saved record).
        work_items.append((path, volume_pending, not lyrics_present))

    print()
    print("曲库：", MUSIC_ROOT)
    print("歌曲数量：", len(files))
    print(f"本次需处理：{len(work_items)}，已有歌词且状态未变而跳过：{cached_count}")
    print("音频已有歌词时不查询新歌词；文件修改时间未变时跳过音量检查")
    print()

    stats = {
        "success": 0,
        "skipped": 0,
        "missing": 0,
        "failed": 0
    }

    print(f"并发线程数：{args.workers}")
    executor = ThreadPoolExecutor(max_workers=args.workers)
    futures = {
        executor.submit(
            process_file,
            path,
            args.overwrite,
            check_volume,
            check_lyrics
        ): (path, check_volume, check_lyrics)
        for path, check_volume, check_lyrics in work_items
    }
    try:
        for index, future in enumerate(as_completed(futures), 1):
            path, check_volume, check_lyrics = futures[future]
            print(f"[{index}/{len(work_items)}] {path.name}")
            try:
                result = future.result()
            except Exception:
                logger.exception("线程处理失败：%s", path)
                result = "failed"

            stats[result] += 1
            if result == "missing":
                missing_files.append(str(path.relative_to(MUSIC_ROOT)))

            try:
                mtime_ns = path.stat().st_mtime_ns
                key = relative_key(path)
                previous = scan_state.get(key, {})
                with _volume_success_lock:
                    volume_succeeded = str(path) in _volume_check_successes
                entry = {
                    "mtime_ns": mtime_ns,
                    "volume_mtime_ns": (
                        mtime_ns if check_volume and volume_succeeded
                        else previous.get("volume_mtime_ns")
                    ),
                    "volume_checked_at": (
                        time.time() if check_volume and volume_succeeded
                        else previous.get("volume_checked_at")
                    ),
                    "lyrics_checked_at": previous.get("lyrics_checked_at"),
                    "result": result
                }
                if check_lyrics and result in {"success", "skipped", "missing"}:
                    entry["lyrics_checked_at"] = time.time()
                elif check_lyrics and previous.get("mtime_ns") != mtime_ns:
                    # A failed lookup on a newly changed file must not inherit
                    # a recent check timestamp from its previous contents.
                    entry["lyrics_checked_at"] = None
                if not check_lyrics:
                    entry["result"] = previous.get("result", result)
                scan_state[key] = entry
                save_scan_result(scan_db, key, entry)
            except OSError:
                logger.exception("无法更新扫描记录：%s", path)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，正在取消排队任务并停止 FFmpeg…")
        _stop_event.set()
        for future in futures:
            future.cancel()
        stop_active_ffmpeg()
        executor.shutdown(wait=True, cancel_futures=True)
        scan_db.close()
        print("程序已停止。")
        return
    else:
        executor.shutdown(wait=True)

    scan_db.close()

    # 保存未找到歌词的歌曲
    missing_path = MUSIC_ROOT / "missing.txt"

    if missing_files:

        missing_path.write_text(
            "\n".join(missing_files),
            encoding="utf-8-sig"
        )

    elif missing_path.exists():

        missing_path.unlink()

    print()
    print("========== 处理结果 ==========")
    print("成功：", stats["success"])
    print("跳过：", stats["skipped"])
    print("未找到：", stats["missing"])
    print("失败：", stats["failed"])
    print()
    print("歌词与扫描记录数据库：", SCAN_DB_PATH)
    print("日志：", MUSIC_ROOT / "lyrics.log")


if __name__ == "__main__":
    main()
