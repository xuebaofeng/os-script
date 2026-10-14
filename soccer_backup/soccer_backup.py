#!/usr/bin/env python3
"""Trace JSON match lookup + SQLite inventory + resumable YouTube backup.

Requires: google-api-python-client google-auth-oauthlib google-auth-httplib2
Run: python soccer_backup.py VIDEO [--db soccer_backup.db]
Trace JSON is auto-detected under the script directory.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB = str(SCRIPT_DIR / "soccer_backup.db")
DEFAULT_CLIENT_SECRETS = str(SCRIPT_DIR / "client_secret.json")
DEFAULT_TOKEN_FILE = str(SCRIPT_DIR / "youtube_token.pickle")
SCHEMA = """
         CREATE TABLE IF NOT EXISTS matches (
                                                game_id INTEGER PRIMARY KEY, full_date TEXT, match_date TEXT, sport_type TEXT,
                                                home_team TEXT, away_team TEXT, home_score INTEGER, away_score INTEGER,
                                                division TEXT, raw_json TEXT, trace_json TEXT, updated_at TEXT
         );
         CREATE TABLE IF NOT EXISTS videos (
                                               id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER NOT NULL, period TEXT NOT NULL,
                                               filename TEXT NOT NULL, full_path TEXT, sha256 TEXT, size_bytes INTEGER,
                                               youtube_video_id TEXT, upload_status TEXT DEFAULT 'pending', upload_session_url TEXT,
                                               uploaded_bytes INTEGER DEFAULT 0, error_message TEXT, last_attempt_at TEXT,
                                               created_at TEXT, updated_at TEXT, UNIQUE(game_id, period)
             ); \
         """

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()
def first(obj, *keys):
    if not isinstance(obj, dict): return None
    for k in keys:
        if k in obj and obj[k] not in (None, ""): return obj[k]
    return None

def init_db(conn):
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(videos)")}
    migrations = {
        "full_path":"TEXT", "sha256":"TEXT", "size_bytes":"INTEGER", "youtube_video_id":"TEXT",
        "upload_status":"TEXT DEFAULT 'pending'", "upload_session_url":"TEXT", "uploaded_bytes":"INTEGER DEFAULT 0",
        "error_message":"TEXT", "last_attempt_at":"TEXT", "created_at":"TEXT", "updated_at":"TEXT"
    }
    for name, typ in migrations.items():
        if name not in cols: conn.execute(f"ALTER TABLE videos ADD COLUMN {name} {typ}")
    mcols = {r[1] for r in conn.execute("PRAGMA table_info(matches)")}
    for name, typ in {"home_team":"TEXT","away_team":"TEXT","home_score":"INTEGER","away_score":"INTEGER","division":"TEXT","raw_json":"TEXT","trace_json":"TEXT","updated_at":"TEXT"}.items():
        if name not in mcols: conn.execute(f"ALTER TABLE matches ADD COLUMN {name} {typ}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_sha256 ON videos(sha256)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_youtube_id ON videos(youtube_video_id)")
    conn.commit()

def extract_matches(data):
    """Find match-like dictionaries anywhere in a Trace export."""
    out=[]; seen=set()
    def walk(x):
        if isinstance(x, dict):
            gid=first(x,"game_id","gameId","match_id","matchId","id")
            # Prefer explicit game IDs and objects containing team/date-like fields.
            if gid is not None and str(gid).isdigit():
                home=first(x,"home_team","homeTeam","home_team_name","homeTeamName")
                away=first(x,"away_team","awayTeam","away_team_name","awayTeamName")
                teams=first(x,"teams","team_names","teamNames")
                if isinstance(teams,list) and len(teams)>=2:
                    home=home or first(teams[0] if isinstance(teams[0],dict) else {},"name","team_name") or (teams[0] if isinstance(teams[0],str) else None)
                    away=away or first(teams[1] if isinstance(teams[1],dict) else {},"name","team_name") or (teams[1] if isinstance(teams[1],str) else None)
                date=first(x,"full_date","fullDate","match_date","matchDate","date","start_time","startTime","kickoff")
                score=first(x,"score","result")
                hs=first(x,"home_score","homeScore","home_goals","homeGoals")
                aws=first(x,"away_score","awayScore","away_goals","awayGoals")
                if isinstance(score,str):
                    m=re.search(r"(\d+)\s*[-:]\s*(\d+)",score)
                    if m: hs=hs if hs is not None else int(m.group(1)); aws=aws if aws is not None else int(m.group(2))
                if isinstance(score,dict):
                    hs=hs if hs is not None else first(score,"home","home_score")
                    aws=aws if aws is not None else first(score,"away","away_score")
                div=first(x,"division","competition","league","team_division")
                if home or away or date or div:
                    rec={"game_id":int(gid),"full_date":str(date or ""),"match_date":str(date or "")[:10],"sport_type":str(first(x,"sport_type","sportType","sport") or "soccer"),"home_team":str(home or ""),"away_team":str(away or ""),"home_score":to_int(hs),"away_score":to_int(aws),"division":str(div or ""),"raw_json":json.dumps(x,ensure_ascii=False)}
                    key=rec["game_id"]
                    if key not in seen: out.append(rec); seen.add(key)
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(data); return out

def to_int(v):
    try: return int(v) if v is not None else None
    except (ValueError,TypeError): return None

def load_trace(path):
    with open(path,"r",encoding="utf-8-sig") as f: return extract_matches(json.load(f))

def discover_trace_json():
    """Find the unique JSON under the script directory containing Trace match records."""
    candidates = []
    for p in SCRIPT_DIR.rglob("*.json"):
        if p.name.lower() in {"client_secret.json", "credentials.json"}:
            continue
        try:
            records = load_trace(p)
        except (OSError, json.JSONDecodeError, UnicodeError, ValueError):
            continue
        if records:
            candidates.append((p, records))
    if len(candidates) == 1:
        print(f"Trace JSON: {candidates[0][0]}")
        return candidates[0]
    if not candidates:
        raise SystemExit(f"No Trace JSON with match records found under {SCRIPT_DIR}")
    print("Multiple Trace JSON files contain match records; cannot safely choose:", file=sys.stderr)
    for p, records in candidates:
        print(f"  {p} ({len(records)} matches)", file=sys.stderr)
    raise SystemExit("Keep only the intended Trace export in this folder, or rename/move other Trace JSON files.")
def upsert_matches(conn, matches):
    for m in matches:
        # Older databases may have a NOT NULL trace_json column. Populate both JSON columns
        # so the script remains compatible with databases created by the earlier importer.
        payload = {**m, "updated_at": now(), "trace_json": m.get("raw_json", "{}")}
        conn.execute("""INSERT INTO matches(game_id,full_date,match_date,sport_type,home_team,away_team,home_score,away_score,division,raw_json,trace_json,updated_at)
                        VALUES(:game_id,:full_date,:match_date,:sport_type,:home_team,:away_team,:home_score,:away_score,:division,:raw_json,:trace_json,:updated_at)
                            ON CONFLICT(game_id) DO UPDATE SET full_date=excluded.full_date,match_date=excluded.match_date,sport_type=excluded.sport_type,home_team=excluded.home_team,away_team=excluded.away_team,home_score=excluded.home_score,away_score=excluded.away_score,division=excluded.division,raw_json=excluded.raw_json,trace_json=excluded.trace_json,updated_at=excluded.updated_at""", payload)
    conn.commit()

def parse_period(path):
    m=re.search(r"(?:^|[-_])period[-_]?([12])(?:[-_.]|$)",Path(path).name,re.I)
    if not m: raise ValueError(f"Cannot determine period from filename: {Path(path).name}; expected period-1 or period-2")
    return m.group(1)+"H"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def match_candidates(matches, path):
    # Directory/file names are evidence, not a substitute for explicit selection if ambiguous.
    hints=norm(" ".join([Path(path).stem, *[p.name for p in list(Path(path).parents)[:3]]]))
    scored=[]
    for m in matches:
        home=norm(m["home_team"]); away=norm(m["away_team"])
        score=0
        if home and home in hints: score+=3
        if away and away in hints: score+=3
        # Use distinctive team-name tokens for filenames such as ALBION ... period-1.
        for team in (home,away):
            toks=[t for t in team.split() if len(t)>3 and t not in {"club","soccer","team","academy","division"}]
            if toks and any(t in hints for t in toks): score+=1
        if score: scored.append((score,m))
    scored.sort(key=lambda z:(-z[0],z[1]["game_id"]))
    if not scored: return []
    top=scored[0][0]
    return [m for s,m in scored if s==top]

def display_match(m):
    score=f"{m.get('home_score') if m.get('home_score') is not None else '?'} - {m.get('away_score') if m.get('away_score') is not None else '?'}"
    return f"game_id={m['game_id']} | {m.get('match_date','')} | {m.get('home_team','')} {score} {m.get('away_team','')} | {m.get('division','')}"

def get_match(conn,gid):
    r=conn.execute("SELECT * FROM matches WHERE game_id=?",(gid,)).fetchone()
    return dict(r) if r else None

def upsert_video(conn,m,path,period,digest,size):
    p=str(Path(path).resolve()); stamp=now()
    old=conn.execute("SELECT * FROM videos WHERE game_id=? AND period=?",(m["game_id"],period)).fetchone()
    if old and old["sha256"] and old["sha256"] != digest:
        raise RuntimeError(f"DB already has a different file for game_id={m['game_id']} period={period}: {old['filename']}")
    conn.execute("""INSERT INTO videos(game_id,period,filename,full_path,sha256,size_bytes,upload_status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,'pending',?,?) ON CONFLICT(game_id,period) DO UPDATE SET filename=excluded.filename,full_path=excluded.full_path,sha256=excluded.sha256,size_bytes=excluded.size_bytes,updated_at=excluded.updated_at""",
                 (m["game_id"],period,Path(path).name,p,digest,size,stamp,stamp))
    conn.commit()
    return conn.execute("SELECT * FROM videos WHERE game_id=? AND period=?",(m["game_id"],period)).fetchone()

def update_video(conn,vid,**kw):
    kw["updated_at"]=now(); sets=", ".join(f"{k}=?" for k in kw)
    conn.execute(f"UPDATE videos SET {sets} WHERE id=?",(*kw.values(),vid)); conn.commit()

def youtube_client(client_secrets, token_file):
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle
    except ImportError as e: raise RuntimeError("Install dependencies: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2") from e
    scopes=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.readonly"]
    creds=None; tf=Path(token_file)
    if tf.exists():
        with tf.open("rb") as f: creds=pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else: creds=InstalledAppFlow.from_client_secrets_file(client_secrets,scopes).run_local_server(port=0)
        with tf.open("wb") as f: pickle.dump(creds,f)
    return build("youtube","v3",credentials=creds)

def find_existing_youtube(youtube, digest, game_id, period):
    # Search uploads playlist descriptions for the stable metadata block.
    channel=youtube.channels().list(part="contentDetails",mine=True).execute()
    items=channel.get("items",[])
    if not items: return None
    playlist=items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    token=None
    while True:
        page=youtube.playlistItems().list(part="snippet,contentDetails",playlistId=playlist,maxResults=50,pageToken=token).execute()
        ids=[x.get("contentDetails",{}).get("videoId") for x in page.get("items",[]) if x.get("contentDetails",{}).get("videoId")]
        for i in range(0,len(ids),50):
            details=youtube.videos().list(part="snippet,description",id=",".join(ids[i:i+50])).execute()
            for v in details.get("items",[]):
                desc=v.get("snippet",{}).get("description","")
                if f"SOCCER_BACKUP_SHA256={digest}" in desc or (f"SOCCER_BACKUP_GAME_ID={game_id}" in desc and f"SOCCER_BACKUP_PERIOD={period}" in desc): return v["id"]
        token=page.get("nextPageToken")
        if not token: break
    return None

def upload(youtube, conn, video_row, match, path, chunk_mb=8):
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError as e: raise RuntimeError("Install google-api-python-client") from e
    from googleapiclient.errors import HttpError
    vid=video_row["id"]; digest=video_row["sha256"]; period=video_row["period"]
    # If SQLite already records a YouTube ID, verify it exists before attempting a duplicate upload.
    existing=video_row["youtube_video_id"]
    if existing:
        try:
            check=youtube.videos().list(part="id,status",id=existing).execute()
            if check.get("items"):
                print(f"Already uploaded: https://youtu.be/{existing}"); return existing
        except Exception: pass
    found=find_existing_youtube(youtube,digest,match["game_id"],period)
    if found:
        update_video(conn,vid,youtube_video_id=found,upload_status="uploaded",error_message=None,upload_session_url=None)
        print(f"Found existing YouTube backup: https://youtu.be/{found}"); return found
    description=(f"Soccer match backup\n\n{display_match(match)}\nOriginal filename: {Path(path).name}\nFull local path: {Path(path).resolve()}\n"
                 f"SHA256: {digest}\n\nSOCCER_BACKUP_GAME_ID={match['game_id']}\nSOCCER_BACKUP_PERIOD={period}\nSOCCER_BACKUP_SHA256={digest}")
    body={"snippet":{"title":f"{match.get('match_date','')} {match.get('home_team','')} vs {match.get('away_team','')} {period}","description":description,"categoryId":"17"},"status":{"privacyStatus":"private"}}
    media=MediaFileUpload(str(path),chunksize=chunk_mb*1024*1024,resumable=True)
    req=youtube.videos().insert(part="snippet,status",body=body,media_body=media)
    update_video(conn,vid,upload_status="uploading",last_attempt_at=now(),error_message=None)
    response=None
    try:
        while response is None:
            status,response=req.next_chunk()
            if status:
                uploaded=int(status.resumable_progress or 0)
                update_video(conn,vid,uploaded_bytes=uploaded)
                print(f"Uploaded {uploaded}/{Path(path).stat().st_size} bytes ({status.progress()*100:.1f}%)")
        yid=response["id"]
        update_video(conn,vid,youtube_video_id=yid,upload_status="uploaded",uploaded_bytes=Path(path).stat().st_size,upload_session_url=None,error_message=None)
        print(f"Upload complete: https://youtu.be/{yid}"); return yid
    except Exception as e:
        update_video(conn,vid,upload_status="error",error_message=str(e)[:2000])
        raise

def main():
    ap=argparse.ArgumentParser(description="Match a local Trace video to a Trace JSON match, register it in SQLite, and upload privately to YouTube.")
    ap.add_argument("filename", help="Video file path")
    ap.add_argument("--db",default=DEFAULT_DB)
    ap.add_argument("--game-id",type=int,help="Explicitly select a match when path matching is ambiguous")
    ap.add_argument("--client-secrets",default=DEFAULT_CLIENT_SECRETS)
    ap.add_argument("--token-file",default=DEFAULT_TOKEN_FILE)
    ap.add_argument("--chunk-mb",type=int,default=8)
    ap.add_argument("--register-only",action="store_true",help="Match/register/hash the video but do not upload")
    args=ap.parse_args()
    path=Path(args.filename)
    if not path.is_file(): ap.error(f"Video file not found: {path}")
    period=parse_period(path)
    trace_path, matches=discover_trace_json()
    if not matches: raise SystemExit("No match records with game IDs and match metadata were found in Trace JSON. Check JSON schema/export.")
    conn=sqlite3.connect(args.db); conn.row_factory=sqlite3.Row; init_db(conn); upsert_matches(conn,matches)
    if args.game_id:
        selected=next((m for m in matches if m["game_id"]==args.game_id),None)
        if not selected: raise SystemExit(f"game_id {args.game_id} not found in Trace JSON")
    else:
        candidates=match_candidates(matches,path)
        if len(candidates)!=1:
            print("Could not safely select exactly one Trace match. Candidates:",file=sys.stderr)
            for m in (candidates if candidates else matches): print("  "+display_match(m),file=sys.stderr)
            print("Re-run with --game-id GAME_ID",file=sys.stderr); raise SystemExit(2)
        selected=candidates[0]
    print("Match: "+display_match(selected)); print("Period: "+period)
    digest=sha256_file(path); size=path.stat().st_size
    row=upsert_video(conn,selected,path,period,digest,size)
    print(f"File: {path.resolve()}\nSHA256: {digest}\nSize: {size} bytes\nDB: {args.db}")
    if args.register_only: return
    yt=youtube_client(args.client_secrets,args.token_file)
    upload(yt,conn,row,selected,path,args.chunk_mb)

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: print("Interrupted.",file=sys.stderr); raise SystemExit(130)
    except Exception as e: print(f"ERROR: {e}",file=sys.stderr); raise SystemExit(1)
