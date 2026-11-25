"""Lane A · step A3 — SQLite store (config.DB_PATH) for results, fingerprints and feedback.

Suggested table: checks(id PK, created_at, tg_file_unique_id, fingerprint JSON, result JSON,
times_checked INT, feedback_correct INT NULL). Linear scan of fingerprints is fine at hackathon scale.
"""


def find(*, tg_file_unique_id: str | None, fp: list[int]) -> dict | None:
    raise NotImplementedError("Lane A · A3: store.find()")


def bump_times_checked(result: dict) -> dict:
    """Increment times_checked; return the result with cache.hit = True and credits_charged = 0."""
    raise NotImplementedError("Lane A · A3: store.bump_times_checked()")


def save(result: dict, *, source: dict, fp: list[int]) -> None:
    raise NotImplementedError("Lane A · A3: store.save()")


def get(result_id: str) -> dict | None:
    """Used by the result page /r/<id>."""
    raise NotImplementedError("Lane A · A3/A4: store.get()")
