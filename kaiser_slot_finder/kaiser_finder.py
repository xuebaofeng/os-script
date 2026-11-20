#!/usr/bin/env python3
# Kaiser appointment slot monitor
# Uses only the user's own authenticated session. Does NOT book appointments.

import copy
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
PAYLOAD_PATH = ROOT / "payload_template.json"
DB_PATH = ROOT / "seen_slots.sqlite3"
LOG_PATH = ROOT / "kaiser_finder.log"
RAW_DIR = ROOT / "raw_responses"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger("kaiser-finder")

DATE_KEYS = {"date", "appointmentdate", "startdate", "localdate", "slotdate"}
TIME_KEYS = {"time", "starttime", "appointmenttime", "slottime", "displaytime"}
STATUS_KEYS = {"available", "isavailable", "availability", "status", "slotstatus"}
ID_KEYS = {"slotid", "appointmentid", "id", "scheduleid"}

def norm(k: Any) -> str:
    return re.sub(r"[^a-z]", "", str(k).lower())

def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS seen (
            fingerprint TEXT PRIMARY KEY,
            first_seen TEXT NOT NULL,
            facility_id TEXT,
            facility_name TEXT,
            slot_date TEXT,
            slot_time TEXT,
            details TEXT
        )""")

def notify(title: str, message: str):
    # Windows toast if winotify is installed; otherwise console + terminal bell.
    print("\a", end="", flush=True)
    try:
        from winotify import Notification, audio
        toast = Notification(app_id="Kaiser Slot Finder", title=title, msg=message)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception:
        log.warning("Windows toast unavailable. Install with: py -m pip install winotify")

def parse_bool_available(obj: dict) -> bool:
    for k, v in obj.items():
        nk = norm(k)
        if nk in {"available", "isavailable"} and v is True:
            return True
        if nk in {"availability", "status", "slotstatus"}:
            s = str(v).strip().lower()
            if s in {"available", "open", "bookable", "free"}:
                return True
    # If response object itself resembles an actual slot and has date + time,
    # treat it as a candidate unless explicitly marked unavailable.
    vals = {norm(k): v for k, v in obj.items()}
    has_date = any(k in vals for k in DATE_KEYS)
    has_time = any(k in vals for k in TIME_KEYS)
    explicitly_unavailable = any(
        norm(k) in {"available", "isavailable"} and v is False for k, v in obj.items()
    )
    return has_date and has_time and not explicitly_unavailable

def extract_candidates(data: Any):
    found = []
    def walk(node):
        if isinstance(node, dict):
            if parse_bool_available(node):
                vals = {norm(k): v for k, v in node.items()}
                d = next((vals[k] for k in DATE_KEYS if k in vals), "")
                t = next((vals[k] for k in TIME_KEYS if k in vals), "")
                sid = next((vals[k] for k in ID_KEYS if k in vals), "")
                found.append({
                    "date": str(d), "time": str(t), "slot_id": str(sid),
                    "details": node
                })
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    # De-duplicate candidates within one response
    out, keys = [], set()
    for item in found:
        key = (item["date"], item["time"], item["slot_id"], json.dumps(item["details"], sort_keys=True, default=str))
        if key not in keys:
            keys.add(key)
            out.append(item)
    return out

def substitute_dates(payload: dict, start: date, end: date):
    p = copy.deepcopy(payload)
    p["fromDate"] = start.strftime("%m/%d/%Y")
    p["toDate"] = end.strftime("%m/%d/%Y")
    return p

def make_fingerprint(facility_id, item):
    raw = "|".join([facility_id, item["date"], item["time"], item["slot_id"]])
    if not item["date"] and not item["time"]:
        raw += "|" + json.dumps(item["details"], sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def save_new(facility, item):
    fp = make_fingerprint(facility["id"], item)
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute(
            "INSERT OR IGNORE INTO seen VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fp, datetime.now().isoformat(timespec="seconds"), facility["id"],
             facility["name"], item["date"], item["time"],
             json.dumps(item["details"], ensure_ascii=False, default=str))
        )
        return cur.rowcount == 1

def main():
    if not CONFIG_PATH.exists() or not PAYLOAD_PATH.exists():
        raise SystemExit("Missing config.json or payload_template.json. See README.txt.")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    template = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    init_db()
    RAW_DIR.mkdir(exist_ok=True)

    url = cfg.get("url", "https://apims.kaiserpermanente.org/kp/mycare/appointment-center/apptctr-bff-kpwebncalmedicalbooking/v1/slots")
    headers = cfg.get("headers", {})
    facilities = cfg.get("facilities", [])
    interval = max(60, int(cfg.get("interval_minutes", 10)) * 60)
    horizon = max(1, int(cfg.get("days_ahead", 30)))
    timeout = int(cfg.get("timeout_seconds", 30))

    if not headers.get("Cookie"):
        raise SystemExit("config.json is missing headers.Cookie. Add your current session cookie locally; never share it.")
    if not facilities:
        raise SystemExit("Add at least one facility to config.json. Only DUB is known from your sample.")

    session = requests.Session()
    session.headers.update(headers)

    log.info("Monitoring %d configured facility/facilities; next %d days; interval %d min.",
             len(facilities), horizon, interval)
    log.info("This program searches only. It will not book or hold an appointment.")

    while True:
        today = date.today()
        end = today + timedelta(days=horizon)
        for facility in facilities:
            try:
                payload = substitute_dates(template, today, end)
                payload["facilityId"] = facility["id"]
                payload["facilityName"] = facility["name"]
                payload["guid"] = int(cfg.get("guid", payload.get("guid", 0)))
                payload["searchTillFirstAvailable"] = True
                payload["searchFirstAvailable"] = True
                payload["maxSlotsToReturn"] = int(cfg.get("max_slots", 100))

                response = session.post(url, json=[payload], timeout=timeout)
                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError:
                    data = {"_non_json_response": response.text[:20000]}

                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                raw_path = RAW_DIR / f"{facility['id']}_{stamp}.json"
                raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

                candidates = extract_candidates(data)
                if not candidates:
                    log.info("%s: response received, but generic parser found no slot objects. Raw: %s",
                             facility["name"], raw_path.name)
                    continue

                for item in candidates:
                    if save_new(facility, item):
                        msg = f"{facility['name']} | {item['date']} {item['time']}"
                        log.warning("NEW POSSIBLE SLOT: %s", msg)
                        notify("Kaiser: possible appointment", msg)

                log.info("%s: %d possible slot record(s).", facility["name"], len(candidates))

            except requests.HTTPError as e:
                body = ""
                try:
                    body = e.response.text[:1000]
                except Exception:
                    pass
                log.error("%s: HTTP error: %s %s", facility["name"], e, body)
            except requests.RequestException as e:
                log.error("%s: network error: %s", facility["name"], e)
            except Exception:
                log.exception("%s: unexpected error", facility.get("name", "facility"))

        log.info("Next scan in %d minutes.", interval // 60)
        time.sleep(interval)

if __name__ == "__main__":
    main()
