import os
import sqlite3
import subprocess
import uuid
import time
import re
import multiprocessing
import random
from concurrent.futures import ProcessPoolExecutor

# =====================
# CONFIG
# =====================
MUSIC_DIR = r"C:\shared\media\CloudMusic"
DB_PATH = "audio_scheduler.db"

SUPPORTED_EXT = {".mp3", ".opus"}

TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0

TMP_DIR = os.path.join(MUSIC_DIR, ".tmp")
os.makedirs(TMP_DIR, exist_ok=True)

MAX_RETRY = 3

CPU_COUNT = multiprocessing.cpu_count()
WORKERS = max(6, CPU_COUNT - 6)   # 16核机器安全值


# =====================
# DB
# =====================
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def init_db():
    conn = db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        path TEXT PRIMARY KEY,
        status TEXT,
        worker_id TEXT,
        retry_count INTEGER DEFAULT 0,
        updated_at REAL
    )
    """)
    conn.commit()
    conn.close()


# =====================
# SCAN
# =====================
def scan():
    conn = db()

    for root, _, files in os.walk(MUSIC_DIR):
        for f in files:

            if not any(f.lower().endswith(ext) for ext in SUPPORTED_EXT):
                continue

            if ".tmp" in f:
                continue

            path = os.path.join(root, f)

            conn.execute("""
                INSERT OR IGNORE INTO tasks(path, status, retry_count, updated_at)
                VALUES (?, 'pending', 0, ?)
            """, (path, time.time()))

    conn.commit()
    conn.close()


# =====================
# CLAIM (atomic + lease timeout)
# =====================
def claim(worker_id):
    conn = db()
    cur = conn.cursor()

    now = time.time()

    cur.execute("""
        UPDATE tasks
        SET status='running',
            worker_id=?,
            updated_at=?
        WHERE path = (
            SELECT path FROM tasks
            WHERE status='pending'
               OR (status='running' AND updated_at < ?)
            LIMIT 1
        )
    """, (worker_id, now, now - 300))

    conn.commit()

    cur.execute("""
        SELECT path, retry_count
        FROM tasks
        WHERE worker_id=? AND status='running'
        ORDER BY updated_at DESC
        LIMIT 1
    """, (worker_id,))

    row = cur.fetchone()
    conn.close()

    return row


# =====================
# TMP FILE
# =====================
def make_tmp(path):
    name = os.path.basename(path)
    base, ext = os.path.splitext(name)
    return os.path.join(TMP_DIR, f"{base}.{uuid.uuid4().hex}{ext}")


# =====================
# FFmpeg JSON parse
# =====================
def parse_ffmpeg(text):
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise RuntimeError("No JSON found")

    import json
    return json.loads(m.group(0))


# =====================
# ANALYZE
# =====================
def analyze(path):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i", path,
        "-af",
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        "-f", "null", "-"
    ]

    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    text = r.stderr.decode("utf-8", errors="ignore")

    return parse_ffmpeg(text)


# =====================
# SAFE REPLACE
# =====================
def safe_replace(src, dst):
    for i in range(5):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.5 * (i + 1))
    raise RuntimeError("file locked too long")


# =====================
# APPLY
# =====================
def apply(path, p):
    tmp = make_tmp(path)
    _, ext = os.path.splitext(path)

    af = (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
        f"measured_I={p['input_i']}:"
        f"measured_TP={p['input_tp']}:"
        f"measured_LRA={p['input_lra']}:"
        f"measured_thresh={p['input_thresh']}:"
        f"offset={p['target_offset']}:"
        f"linear=true"
    )

    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", path]

    if ext.lower() == ".mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]
    else:
        cmd += ["-c:a", "libopus", "-b:a", "128k"]

    cmd += ["-af", af, tmp]

    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", errors="ignore"))

    safe_replace(tmp, path)


# =====================
# WORKER
# =====================
def worker(worker_id):
    while True:

        time.sleep(random.uniform(0.05, 0.2))  # 防抢锁

        task = claim(worker_id)
        if not task:
            break

        path, retry = task

        print(f"[{worker_id}] {path}")

        try:
            p = analyze(path)
            apply(path, p)

            conn = db()
            conn.execute("""
                UPDATE tasks
                SET status='done', updated_at=?
                WHERE path=?
            """, (time.time(), path))
            conn.commit()
            conn.close()

        except Exception as e:

            conn = db()

            if retry >= MAX_RETRY:
                conn.execute("UPDATE tasks SET status='failed' WHERE path=?", (path,))
                print(f"[FAILED FINAL] {path}")
            else:
                conn.execute("""
                    UPDATE tasks
                    SET status='pending',
                        retry_count=retry_count+1
                    WHERE path=?
                """, (path,))
                print(f"[RETRY {retry}] {path}")

            conn.commit()
            conn.close()


# =====================
# MAIN
# =====================
def main():
    init_db()
    scan()

    print(f"CPU cores: {CPU_COUNT}, workers: {WORKERS}")

    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for i in range(WORKERS):
            ex.submit(worker, str(uuid.uuid4()))


if __name__ == "__main__":
    main()