"""Lane A · step A3 — SQLite store (config.DB_PATH) for results, fingerprints and feedback.

The bot and the web server are separate processes sharing this file, so: WAL mode, a busy
timeout, and a short-lived connection per call. Linear fingerprint scan is fine at hackathon scale,
and it only compares clips of similar length.
"""
import json
import sqlite3
import time
from contextlib import contextmanager

from app import config
from app.core import fingerprint

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
  times_checked INTEGER NOT NULL DEFAULT 1
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
"""
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
            _ready_for = str(config.DB_PATH)
        con.execute("PRAGMA busy_timeout=10000")
        yield con
        con.commit()
    finally:
        con.close()


def _duration_window(duration: float) -> tuple[float, float]:
    slack = max(3.0, 0.15 * duration)
    return duration - slack, duration + slack


def _as_hit(row: sqlite3.Row) -> dict:
    r = json.loads(row["result"])
    r["cache"] = {"hit": True, "times_checked": row["times_checked"]}
    r["credits_charged"] = 0
    return r


def find_exact(*, tg_file_unique_id: str | None = None, sha256: str | None = None) -> str | None:
    """Return the id of a cached (non-error) check for this exact file, if any."""
    with _db() as con:
        for col, val in (("tg_file_unique_id", tg_file_unique_id), ("sha256", sha256)):
            if val:
                row = con.execute(f"SELECT id FROM checks WHERE {col}=? AND band!='error' "
                                  "ORDER BY created_at LIMIT 1", (val,)).fetchone()
                if row:
                    return row["id"]
    return None


def has_candidates(duration: float) -> bool:
    lo, hi = _duration_window(duration)
    with _db() as con:
        return con.execute("SELECT 1 FROM checks WHERE fp IS NOT NULL AND band!='error' "
                           "AND duration BETWEEN ? AND ? LIMIT 1", (lo, hi)).fetchone() is not None


def find_similar(fp: list[int] | None, duration: float) -> tuple[str, float] | None:
    """Best matching cached check (id, similarity) at or above fingerprint.SAME_CLIP."""
    if not fp:
        return None
    lo, hi = _duration_window(duration)
    with _db() as con:
        rows = con.execute("SELECT id, fp FROM checks WHERE fp IS NOT NULL AND band!='error' "
                           "AND duration BETWEEN ? AND ?", (lo, hi)).fetchall()
    best = max(((r["id"], fingerprint.similarity(fp, json.loads(r["fp"]))) for r in rows),
               key=lambda t: t[1], default=None)
    return best if best and best[1] >= fingerprint.SAME_CLIP else None


def hit(check_id: str, *, tg_file_unique_id: str | None = None) -> dict:
    """Count one more check of a cached clip; return it shaped as a cache hit (0 credits)."""
    now = time.time()
    with _db() as con:
        con.execute("UPDATE checks SET times_checked = times_checked + 1, last_checked_at=? WHERE id=?",
                    (now, check_id))
        if tg_file_unique_id:  # remember this Telegram file too, so the next forward is tier-1
            con.execute("UPDATE checks SET tg_file_unique_id = COALESCE(tg_file_unique_id, ?) WHERE id=?",
                        (tg_file_unique_id, check_id))
        row = con.execute("SELECT * FROM checks WHERE id=?", (check_id,)).fetchone()
    return _as_hit(row)


def save(result: dict, *, source: dict, sha256: str | None, fp: list[int] | None,
         duration: float | None, audio_path: str | None) -> None:
    now = time.time()
    with _db() as con:
        con.execute(
            "INSERT OR REPLACE INTO checks (id, created_at, last_checked_at, sha256, tg_file_unique_id, channel,"
            " duration, fp, audio_path, band, result, times_checked) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
            (result["id"], now, now, sha256, source.get("tg_file_unique_id"), source.get("channel"),
             duration, json.dumps(fp) if fp else None, audio_path, result["band"],
             json.dumps(result, ensure_ascii=False)))


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
