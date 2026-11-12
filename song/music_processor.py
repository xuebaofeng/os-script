
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
from concurrent.futures import ThreadPoolExecutor, as_completed

from pathlib import Path
from difflib import SequenceMatcher
from mutagen import File
from mutagen.id3 import ID3, USLT, SYLT
from mutagen.mp4 import MP4

# ==================== 配置 ====================

MUSIC_ROOT = Path(r"C:\shared\media\CloudMusic")
LYRICS_ROOT = MUSIC_ROOT / "lyrics"

API = "https://lrclib.net"

SUPPORTED = {
    ".mp3",
    ".m4a",
    ".flac",
    ".opus",
    ".ogg"
}

REQUEST_INTERVAL = 1.0
DEFAULT_WORKERS = 4
NORMALIZE_EXTENSIONS = {".mp3", ".opus"}
TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0
LOUDNESS_TOLERANCE = 1.0
TRUE_PEAK_TOLERANCE = 0.5
LRA_TOLERANCE = 1.0

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
_next_request_at = 0.0


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


def analyze_loudness(path):
    command = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af",
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False
    )
    output = result.stderr.decode("utf-8", errors="ignore")
    match = re.search(r"\{[\s\S]*\}", output)
    if result.returncode != 0 or not match:
        raise RuntimeError(f"FFmpeg 响度分析失败：{output[-1000:]}")
    return json.loads(match.group(0))


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
        "-map_metadata", "0", "-af", filter_value,
        *codec_args, str(temporary_path)
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False
        )
        if result.returncode != 0:
            output = result.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg 响度标准化失败：{output[-1000:]}")

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

def get_lyrics(meta):

    params = {
        "artist_name": meta["artist"],
        "track_name": meta["title"]
    }

    if meta["album"]:
        params["album_name"] = meta["album"]

    if meta["duration"]:
        params["duration"] = meta["duration"]

    try:

        # 第一阶段：精确查询
        response = rate_limited_get(
            f"{API}/api/get",
            params=params,
            timeout=20
        )

        if response.status_code == 200:

            data = response.json()

            if not data.get("instrumental") and (
                data.get("plainLyrics")
                or data.get("syncedLyrics")
            ):
                return data

        elif response.status_code == 429:

            logger.warning("API 限流")
            time.sleep(
                int(response.headers.get("Retry-After", 10))
            )
            return None

        # 第二阶段：搜索候选歌词
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

            if title_score < 0.95:
                continue

            if artist_score < 0.90:
                continue

            if meta["duration"] and item.get("duration"):

                if abs(
                    meta["duration"] - item["duration"]
                ) > 5:
                    continue

            if (
                item.get("plainLyrics")
                or item.get("syncedLyrics")
            ):
                return item

    except requests.RequestException as e:

        logger.error("API 请求失败：%s", e)

    return None


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


# ==================== 保存 LRC ====================

def save_lrc(path, root, synced):

    if not synced:
        return

    relative = path.relative_to(root)

    lrc_path = (
        LYRICS_ROOT / relative
    ).with_suffix(".lrc")

    lrc_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    lrc_path.write_text(
        synced,
        encoding="utf-8-sig"
    )


# ==================== 单曲处理 ====================

def process_file(path, overwrite=False, normalize=True):

    try:

        if normalize:
            normalize_audio(path)

        if (
            has_existing_lyrics(path)
            and not overwrite
        ):

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

        data = get_lyrics(meta)

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

        # 嵌入音频
        embed_lyrics(
            path,
            plain,
            synced
        )

        # 保存 LRC
        save_lrc(
            path,
            MUSIC_ROOT,
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

    LYRICS_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

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

    print()
    print("曲库：", MUSIC_ROOT)
    print("歌词：", LYRICS_ROOT)
    print("歌曲数量：", len(files))
    print("响度标准化：默认开启（已达标的 MP3/Opus 会跳过）")
    print()

    stats = {
        "success": 0,
        "skipped": 0,
        "missing": 0,
        "failed": 0
    }

    missing_files = []

    print(f"并发线程数：{args.workers}")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                process_file, path, args.overwrite, True
            ): path
            for path in files
        }

        for index, future in enumerate(as_completed(futures), 1):
            path = futures[future]
            print(f"[{index}/{len(files)}] {path.name}")
            try:
                result = future.result()
            except Exception:
                logger.exception("线程处理失败：%s", path)
                result = "failed"

            stats[result] += 1
            if result == "missing":
                missing_files.append(str(path.relative_to(MUSIC_ROOT)))

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
    print("歌词目录：", LYRICS_ROOT)
    print("日志：", MUSIC_ROOT / "lyrics.log")


if __name__ == "__main__":
    main()
