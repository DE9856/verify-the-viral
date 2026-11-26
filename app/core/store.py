"""Lane A · step A3 — SQLite store (config.DB_PATH) for results, fingerprints and feedback.

The bot and the web server are separate processes sharing this file, so: WAL mode, a busy
timeout, and a short-lived connection per call. Linear fingerprint scan is fine at hackathon scale,
and it only compares clips of similar length.
"""
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager

from app import config
from app.core import fingerprint, fpdiff

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
  id TEXT PRIMARY KEY,
  created_at REAL NOT NULL,
  last_checked_at REAL NOT NULL,
  sha256 TEXT,
  tg_file_unique_id TEXT,
  channel TEXT,
  duration REAL,
  fp TEXT,
  audio_path TEXT,
  band TEXT NOT NULL,
  result TEXT NOT NULL,
  times_checked INTEGER NOT NULL DEFAULT 1,
  pcm_sha256 TEXT
);
CREATE INDEX IF NOT EXISTS checks_sha ON checks(sha256);
CREATE INDEX IF NOT EXISTS checks_tg ON checks(tg_file_unique_id);
CREATE INDEX IF NOT EXISTS checks_dur ON checks(duration);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_id TEXT NOT NULL,
  operation_id TEXT,
  correct INTEGER NOT NULL,
  label TEXT,
  channel TEXT,
  created_at REAL NOT NULL
);
-- one row per check of a clip (first check and every repeat), for the AI-clip radar.
-- place = "tg:<salted hash of the chat id>" | "share" | channel: we count chats, never store them.
CREATE TABLE IF NOT EXISTS sightings (
  check_id TEXT NOT NULL,
  at REAL NOT NULL,
  channel TEXT,
  place TEXT
);
CREATE INDEX IF NOT EXISTS sightings_check ON sightings(check_id);
"""
# the radar lists a flagged clip only once it is circulating, so a private voice note that was
# checked once (and maybe wrongly flagged) never appears on a public page
RADAR_MIN_PLACES = 2
RADAR_MIN_CHECKS = 3
RADAR_BANDS = ("likely_fake", "partly_fake")
# DetectifAI pricing (docs: 2 credits per second, 20 minimum), to estimate what a repeat would have cost
CREDITS_PER_SECOND, MIN_CREDITS = 2, 20
_ready_for: str | None = None


@contextmanager
def _db():
    global _ready_for
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        if _ready_for != str(config.DB_PATH):
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript(SCHEMA)
            _migrate(con)
            _ready_for = str(config.DB_PATH)
        con.execute("PRAGMA busy_timeout=10000")
        yield con
        con.commit()
    finally:
        con.close()


def _migrate(con: sqlite3.Connection) -> None:
    """Bring a database made by an older version up to date (CREATE IF NOT EXISTS adds no columns)."""
    cols = {r["name"] for r in con.execute("PRAGMA table_info(checks)")}
    if "pcm_sha256" not in cols:
        con.execute("ALTER TABLE checks ADD COLUMN pcm_sha256 TEXT")
    con.execute("CREATE INDEX IF NOT EXISTS checks_pcm ON checks(pcm_sha256)")


def _duration_window(duration: float) -> tuple[float, float]:
    slack = max(3.0, 0.15 * duration)
    return duration - slack, duration + slack


def _as_hit(row: sqlite3.Row) -> dict:
    r = json.loads(row["result"])
    r["cache"] = {"hit": True, "times_checked": row["times_checked"]}
    r["credits_charged"] = 0
    return r


def find_exact(*, tg_file_unique_id: str | None = None, sha256: str | None = None,
               pcm_sha256: str | None = None) -> str | None:
    """Return the id of a cached (non-error) check for this exact file or exact decoded audio, if any."""
    with _db() as con:
        for col, val in (("tg_file_unique_id", tg_file_unique_id), ("sha256", sha256),
                         ("pcm_sha256", pcm_sha256)):
            if val:
                row = con.execute(f"SELECT id FROM checks WHERE {col}=? AND band!='error' "
                                  "ORDER BY created_at LIMIT 1", (val,)).fetchone()
                if row:
                    return row["id"]
    return None


def fp_candidates(lo: float, hi: float) -> list[tuple[str, list[int], float, int]]:
    """Stored (non-error) clips with a fingerprint and a length in [lo, hi]:
    (id, fingerprint, duration, times_checked), most-checked first. Used by variants.py."""
    with _db() as con:
        rows = con.execute("SELECT id, fp, duration, times_checked FROM checks WHERE fp IS NOT NULL AND band!='error' "
                           "AND duration BETWEEN ? AND ? ORDER BY times_checked DESC, last_checked_at DESC",
                           (lo, hi)).fetchall()
    return [(r["id"], json.loads(r["fp"]), r["duration"], r["times_checked"]) for r in rows]


def has_candidates(duration: float, lo: float | None = None, hi: float | None = None) -> bool:
    """Any stored clip to compare against: of similar length, or in [lo, hi] when given."""
    if lo is None or hi is None:
        lo, hi = _duration_window(duration)
    with _db() as con:
        return con.execute("SELECT 1 FROM checks WHERE fp IS NOT NULL AND band!='error' "
                           "AND duration BETWEEN ? AND ? LIMIT 1", (lo, hi)).fetchone() is not None


EDIT_LENGTH = 0.4        # an edited copy can be up to 40 % longer or shorter (inserted / cut seconds)


def match_fingerprint(fp: list[int] | None, duration: float):
    """Layer 4: ((id, similarity) of the same clip, or None), ((id, Diff) of a clip this is an edited
    copy of, or None). Same clip = similarity >= SAME_CLIP AND the diff finds nothing changed; a
    whole-clip score alone lets a few fake seconds inside a known clip through (research/false-match.md)."""
    if not fp:
        return None, None
    with _db() as con:
        rows = con.execute("SELECT id, fp FROM checks WHERE fp IS NOT NULL AND band!='error' "
                           "AND duration BETWEEN ? AND ?",
                           (duration * (1 - EDIT_LENGTH), duration * (1 + EDIT_LENGTH))).fetchall()
    scored = sorted(((fingerprint.similarity(fp, f), r["id"], f) for r in rows for f in [json.loads(r["fp"])]),
                    key=lambda t: t[0], reverse=True)
    edited = None
    for sim, cid, f in scored:
        if sim < fpdiff.NEAR:
            break
        d = fpdiff.diff(fp, f)
        if d.same and sim >= fingerprint.SAME_CLIP:
            return (cid, sim), None
        if d.verdict == "edited" and edited is None:
            edited = (cid, d)
    return None, edited


def find_similar(fp: list[int] | None, duration: float) -> tuple[str, float] | None:
    """The same clip (id, similarity), checked by the diff; see match_fingerprint."""
    return match_fingerprint(fp, duration)[0]


def _salt() -> str:
    """Random per-install secret, so a chat's code can't be turned back into its chat id."""
    path = config.DB_PATH.parent / "radar_salt"
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        salt = secrets.token_hex(16)
        try:
            with open(path, "x", encoding="utf-8") as f:   # first writer wins
                f.write(salt)
            return salt
        except FileExistsError:
            return path.read_text(encoding="utf-8").strip()


def place_of(source: dict | None) -> str | None:
    if not source:
        return None
    chat = source.get("chat_id")
    if source.get("channel") == "telegram" and chat is not None:
        return "tg:" + hashlib.sha256(f"{_salt()}:{chat}".encode()).hexdigest()[:16]
    return source.get("channel")


def _sighting(con, check_id: str, now: float, source: dict | None) -> None:
    if source is not None:
        con.execute("INSERT INTO sightings (check_id, at, channel, place) VALUES (?,?,?,?)",
                    (check_id, now, source.get("channel"), place_of(source)))


def hit(check_id: str, *, tg_file_unique_id: str | None = None, source: dict | None = None) -> dict:
    """Count one more check of a cached clip; return it shaped as a cache hit (0 credits)."""
    now = time.time()
    with _db() as con:
        con.execute("UPDATE checks SET times_checked = times_checked + 1, last_checked_at=? WHERE id=?",
                    (now, check_id))
        _sighting(con, check_id, now, source)
        if tg_file_unique_id:  # remember this Telegram file too, so the next forward is tier-1
            con.execute("UPDATE checks SET tg_file_unique_id = COALESCE(tg_file_unique_id, ?) WHERE id=?",
                        (tg_file_unique_id, check_id))
        row = con.execute("SELECT * FROM checks WHERE id=?", (check_id,)).fetchone()
    return _as_hit(row)


def save(result: dict, *, source: dict, sha256: str | None, fp: list[int] | None,
         duration: float | None, audio_path: str | None, pcm_sha256: str | None = None) -> None:
    now = time.time()
    with _db() as con:
        con.execute(
            "INSERT OR REPLACE INTO checks (id, created_at, last_checked_at, sha256, tg_file_unique_id, channel,"
            " duration, fp, audio_path, band, result, times_checked, pcm_sha256)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?)",
            (result["id"], now, now, sha256, source.get("tg_file_unique_id"), source.get("channel"),
             duration, json.dumps(fp) if fp else None, audio_path, result["band"],
             json.dumps(result, ensure_ascii=False), pcm_sha256))
        _sighting(con, result["id"], now, source)


def get(check_id: str) -> dict | None:
    """The stored result with the current times_checked (used by /r/<id> and /api/result/<id>)."""
    with _db() as con:
        row = con.execute("SELECT result, times_checked FROM checks WHERE id=?", (check_id,)).fetchone()
    if not row:
        return None
    r = json.loads(row["result"])
    r["cache"] = {"hit": r["cache"]["hit"], "times_checked": row["times_checked"]}
    return r


def audio_path(check_id: str) -> str | None:
    with _db() as con:
        row = con.execute("SELECT audio_path FROM checks WHERE id=?", (check_id,)).fetchone()
    return row["audio_path"] if row else None


def add_feedback(check_id: str, operation_id: str | None, correct: bool, label: str | None,
                 channel: str | None = None) -> None:
    with _db() as con:
        con.execute("INSERT INTO feedback (check_id, operation_id, correct, label, channel, created_at)"
                    " VALUES (?,?,?,?,?,?)", (check_id, operation_id, int(correct), label, channel, time.time()))


def operation_id_for(check_id: str) -> str | None:
    r = get(check_id)
    return r.get("operation_id") if r else None


def check_id_for_operation(operation_id: str) -> str | None:
    with _db() as con:
        row = con.execute("SELECT id FROM checks WHERE json_extract(result, '$.operation_id') = ? LIMIT 1",
                          (operation_id,)).fetchone()
    return row["id"] if row else None


def stats() -> dict:
    with _db() as con:
        c = con.execute("SELECT COUNT(*) n, COALESCE(SUM(times_checked),0) t FROM checks").fetchone()
        f = con.execute("SELECT COUNT(*) n, COALESCE(SUM(correct),0) ok FROM feedback").fetchone()
    return {"clips": c["n"], "checks": c["t"], "cache_hits": c["t"] - c["n"],
            "feedback": f["n"], "feedback_correct": f["ok"]}


def radar(*, days: float = 7, limit: int = 30) -> dict:
    """Flagged clips that are circulating (real API results only), newest activity first."""
    since = time.time() - days * 86400
    marks = ",".join("?" * len(RADAR_BANDS))
    with _db() as con:
        rows = con.execute(
            f"SELECT c.id, c.band, c.created_at, c.last_checked_at, c.times_checked, c.duration, c.result,"
            f" (SELECT COUNT(DISTINCT place) FROM sightings s WHERE s.check_id = c.id) AS places"
            f" FROM checks c WHERE c.band IN ({marks}) AND c.last_checked_at >= ?"
            f" AND COALESCE(c.channel, '') != 'live'"                      # a live call is private, never public
            f" AND json_extract(c.result, '$.operation_id') IS NOT NULL"   # mock results have none
            f" ORDER BY c.last_checked_at DESC", (*RADAR_BANDS, since)).fetchall()
        totals = con.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(times_checked),0) t,"
            " COALESCE(SUM((times_checked - 1) * MAX(?, CAST(ROUND(? * COALESCE(duration, 0)) AS INTEGER))),0) saved"
            " FROM checks WHERE band != 'error' AND json_extract(result, '$.operation_id') IS NOT NULL",
            (MIN_CREDITS, CREDITS_PER_SECOND)).fetchone()
        # edited copies (edits.py) paid only for their new seconds, or nothing: full price minus what they
        # cost, plus repeats of the free ones (no operation_id, so the query above skips them)
        edited = con.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(MAX(?, CAST(ROUND(? * COALESCE(duration, 0)) AS INTEGER))"
            " * (CASE WHEN json_extract(result, '$.operation_id') IS NULL THEN times_checked ELSE 1 END)"
            " - COALESCE(json_extract(result, '$.credits_charged'), 0)),0) saved"
            " FROM checks WHERE json_extract(result, '$.edited_copy_of.mode') IS NOT NULL",
            (MIN_CREDITS, CREDITS_PER_SECOND)).fetchone()
    items = []
    for r in rows:
        places = max(r["places"], 1)    # clips checked before sightings existed were still seen once
        if places < RADAR_MIN_PLACES and r["times_checked"] < RADAR_MIN_CHECKS:
            continue
        res = json.loads(r["result"])
        items.append({"id": r["id"], "band": r["band"], "times_checked": r["times_checked"],
                      "places": places, "first_seen": r["created_at"], "last_seen": r["last_checked_at"],
                      "duration": r["duration"] or res.get("duration"), "core_regions": res.get("core_regions", []),
                      "segments": [{"start": s["start"], "end": s["end"], "verdict": s.get("verdict")}
                                   for s in res.get("segments", [])]})
        if len(items) >= limit:
            break
    return {"items": items,
            "stats": {"clips": totals["n"], "checks": totals["t"], "repeats": totals["t"] - totals["n"],
                      "credits_saved": int(totals["saved"]) + int(edited["saved"]),
                      "edited_copies": edited["n"], "credits_saved_on_edits": int(edited["saved"])},
            "rules": {"min_places": RADAR_MIN_PLACES, "min_checks": RADAR_MIN_CHECKS, "days": days}}
