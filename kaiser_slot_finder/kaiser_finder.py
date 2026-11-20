#!/usr/bin/env python3
# Kaiser appointment slot finder
# Uses only the user's own authenticated session. Does NOT book appointments.
#
# Usage:
#   py kaiser_finder.py              # query with current credentials
#   py kaiser_finder.py --update     # paste a new curl first, then query
#   py kaiser_finder.py --update-only  # update credentials only, no query

import copy
import hashlib
import json
import logging
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT         = Path(__file__).resolve().parent
CONFIG_PATH  = ROOT / "config.json"
PAYLOAD_PATH = ROOT / "payload_template.json"
DB_PATH      = ROOT / "seen_slots.sqlite3"
LOG_PATH     = ROOT / "kaiser_finder.log"
RAW_DIR      = ROOT / "raw_responses"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger("kaiser-finder")


# ── credential update ────────────────────────────────────────────────────────

def _unescape_windows(s: str) -> str:
    s = re.sub(r'\^\n\s*', ' ', s)
    s = s.replace("^^", "^").replace("^%", "%").replace('^"', '"').replace("^&", "&")
    return s

def _extract_cookie(curl: str) -> str | None:
    for pat in [
        r"-H\s+\$?'Cookie:\s*(.*?)'(?=\s+-[HX]|\s*\\|\s*$)",
        r'-H\s+"Cookie:\s*(.*?)"(?=\s+-[HX]|\s*\\|\s*$)',
    ]:
        m = re.search(pat, curl, re.DOTALL)
        if m:
            return m.group(1).strip()
    return None

def _extract_session_id(curl: str) -> str | None:
    m = re.search(r'"sessionId"\s*:\s*"(KBE_[^"]+)"', curl)
    return m.group(1) if m else None

def _extract_guid(curl: str) -> int | None:
    m = re.search(r'"guid"\s*:\s*(\d+)', curl)
    return int(m.group(1)) if m else None

def _extract_pcp_service_state(curl: str) -> str | None:
    m = re.search(r'"pcpServiceState"\s*:\s*"([^"]+)"', curl)
    return m.group(1) if m else None

def _clear_query_cache():
    if not DB_PATH.exists():
        return
    with sqlite3.connect(DB_PATH) as db:
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "query_cache" in tables:
            db.execute("DELETE FROM query_cache")
            db.commit()

def update_credentials():
    print("Paste curl command, then press Enter twice:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    curl = _unescape_windows("\n".join(lines))
    cookie     = _extract_cookie(curl)
    session_id = _extract_session_id(curl)
    guid       = _extract_guid(curl)
    pcp        = _extract_pcp_service_state(curl)

    if not cookie:
        sys.exit("Could not extract Cookie from curl.")
    if not session_id:
        sys.exit("Could not extract sessionId from curl payload.")

    m     = re.search(r'MyChartAccessToken4mychartcn=([^;]+)', cookie)
    token = m.group(1) if m else None

    cfg      = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    template = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8-sig"))

    cfg["headers"]["Cookie"] = cookie
    if token:
        cfg["headers"]["Authorization"] = f"Bearer {token}"
    if guid:
        cfg["guid"] = guid
    for f in cfg.get("facilities", []):
        f["sessionId"] = session_id
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    template["sessionId"] = session_id
    if guid:
        template["guid"] = guid
    if pcp:
        template["pcpServiceState"] = pcp
    PAYLOAD_PATH.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")

    _clear_query_cache()

    updated = {"sessionId": session_id}
    if guid:
        updated["guid"] = guid
    if pcp:
        updated["pcpServiceState"] = pcp[:30] + "..."
    updated["Cookie"]    = "..." + cookie[-40:]
    if token:
        updated["Bearer"] = "..." + token[-40:]

    print("\nCredentials updated:")
    for k, v in updated.items():
        print(f"  {k}: {v}")
    print()


# ── database ─────────────────────────────────────────────────────────────────

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
        db.execute("""CREATE TABLE IF NOT EXISTS query_cache (
            facility_id TEXT PRIMARY KEY,
            last_queried_date TEXT NOT NULL
        )""")

def was_queried_today(facility_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT last_queried_date FROM query_cache WHERE facility_id = ?",
            (facility_id,)
        ).fetchone()
    return row is not None and row[0] == date.today().isoformat()

def mark_queried_today(facility_id: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT OR REPLACE INTO query_cache VALUES (?, ?)",
            (facility_id, date.today().isoformat())
        )

def save_new(facility, item) -> bool:
    raw = "|".join([facility["id"], item["date"], item["time"], item["slot_id"]])
    if not item["date"] and not item["time"]:
        raw += "|" + json.dumps(item["details"], sort_keys=True, default=str)
    fp = hashlib.sha256(raw.encode()).hexdigest()
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute(
            "INSERT OR IGNORE INTO seen VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fp, datetime.now().isoformat(timespec="seconds"), facility["id"],
             facility["name"], item["date"], item["time"],
             json.dumps(item["details"], ensure_ascii=False, default=str))
        )
        return cur.rowcount == 1


# ── slot parsing ─────────────────────────────────────────────────────────────

def extract_candidates(data: Any):
    found: list = []
    seen_keys: set = set()

    def add(slot: dict, provider_name: str = ""):
        start = slot.get("start", "")
        key   = (start, slot.get("end", ""), slot.get("facilityId", ""),
                 slot.get("providerName", provider_name))
        if key in seen_keys:
            return
        seen_keys.add(key)
        found.append({
            "date":    start[:10] if start else "",
            "time":    start[11:16] if len(start) > 10 else "",
            "slot_id": f"{slot.get('facilityId','')}_{start}",
            "details": {
                "start":           start,
                "end":             slot.get("end", ""),
                "facilityId":      slot.get("facilityId", ""),
                "facilityName":    slot.get("facilityName", ""),
                "providerName":    slot.get("providerName", provider_name),
                "departmentName":  slot.get("departmentName", ""),
                "isThisAVideoAppt": slot.get("isThisAVideoAppt", False),
            }
        })

    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        for slot in item.get("slots", []):
            if isinstance(slot, dict) and slot.get("start"):
                add(slot)
        for provider in item.get("providers", []):
            if not isinstance(provider, dict):
                continue
            pname = provider.get("providerName", "")
            for slot in provider.get("slots", []):
                if isinstance(slot, dict) and slot.get("start"):
                    add(slot, pname)
    return found


# ── display ───────────────────────────────────────────────────────────────────

def fmt_time(iso: str) -> str:
    try:
        dt   = datetime.fromisoformat(iso)
        day  = dt.strftime("%a, %b ") + str(dt.day)
        hour = dt.hour % 12 or 12
        ampm = "am" if dt.hour < 12 else "pm"
        return f"{day}  {hour}:{dt.minute:02d} {ampm}"
    except Exception:
        return iso[:16]

def notify(title: str, message: str):
    print("\a", end="", flush=True)
    try:
        from winotify import Notification, audio
        toast = Notification(app_id="Kaiser Slot Finder", title=title, msg=message)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception:
        pass


# ── main query ────────────────────────────────────────────────────────────────

def query():
    cfg      = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    template = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8-sig"))
    init_db()
    RAW_DIR.mkdir(exist_ok=True)

    url        = cfg.get("url", "https://apims.kaiserpermanente.org/kp/mycare/appointment-center/apptctr-bff-kpwebncalmedicalbooking/v1/slots")
    headers    = cfg.get("headers", {})
    facilities = cfg.get("facilities", [])
    horizon    = max(1, int(cfg.get("days_ahead", 30)))
    timeout    = int(cfg.get("timeout_seconds", 30))

    if not headers.get("Cookie"):
        raise SystemExit("config.json is missing headers.Cookie.")
    if not facilities:
        raise SystemExit("No facilities configured.")

    session = requests.Session()
    session.headers.update(headers)

    log.info("Querying %d facility/facilities; next %d days.", len(facilities), horizon)

    today = date.today()
    end   = today + timedelta(days=horizon)

    for facility in facilities:
        try:
            if was_queried_today(facility["id"]):
                log.info("%s: already queried today, skipping.", facility["name"])
                continue

            payload = copy.deepcopy(template)
            payload["fromDate"]    = today.strftime("%m/%d/%Y")
            payload["toDate"]      = end.strftime("%m/%d/%Y")
            payload["facilityId"]  = facility["id"]
            payload["facilityName"]= facility["name"]
            payload["guid"]        = int(cfg.get("guid", payload.get("guid", 0)))
            payload["searchTillFirstAvailable"] = True
            payload["searchFirstAvailable"]     = True
            payload["maxSlotsToReturn"]         = int(cfg.get("max_slots", 100))
            for key in ("sessionId", "pcpServiceState", "bookingId"):
                if facility.get(key):
                    payload[key] = facility[key]
                    if key == "bookingId":
                        payload["bookingGuidelineId"] = facility[key]

            response = session.post(url, json=[payload], timeout=timeout)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                data = {"_non_json_response": response.text[:20000]}

            stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_path = RAW_DIR / f"{facility['id']}_{stamp}.json"
            raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

            candidates = extract_candidates(data)
            mark_queried_today(facility["id"])

            if not candidates:
                log.info("%s: no slots found.", facility["name"])
                print(f"\n{facility['name']}: no slots available.")
                continue

            new_count = 0
            print(f"\n{'='*55}")
            print(f"  {facility['name']}  ({len(candidates)} slot(s))")
            print(f"{'='*55}")
            for item in candidates:
                is_new = save_new(facility, item)
                if is_new:
                    new_count += 1
                d          = item["details"]
                provider   = d.get("providerName", "Unknown")
                dept       = d.get("departmentName", "")
                appt_type  = "Video Visit" if d.get("isThisAVideoAppt") else "In-person Visit"
                time_label = fmt_time(d.get("start", ""))
                new_tag    = "  ★ NEW" if is_new else ""
                print(f"  {provider}{new_tag}")
                print(f"  {dept}")
                print(f"  {time_label}")
                print(f"  {appt_type}")
                print()
                if is_new:
                    notify("Kaiser: appointment available",
                           f"{facility['name']} | {time_label} | {provider}")

            log.info("%s: %d slot(s), %d new.", facility["name"], len(candidates), new_count)

        except requests.HTTPError as e:
            body = ""
            try:
                body = json.dumps(e.response.json(), indent=2, ensure_ascii=False)
            except Exception:
                try:
                    body = e.response.text[:3000]
                except Exception:
                    pass
            log.error("%s: HTTP %s  %s", facility["name"], e, body)
        except requests.RequestException as e:
            log.error("%s: network error: %s", facility["name"], e)
        except Exception:
            log.exception("%s: unexpected error", facility.get("name", "facility"))


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    do_update = "--update" in args or "--update-only" in args
    do_query  = "--update-only" not in args

    if not CONFIG_PATH.exists() or not PAYLOAD_PATH.exists():
        raise SystemExit("Missing config.json or payload_template.json.")

    if do_update:
        update_credentials()

    if do_query:
        query()
