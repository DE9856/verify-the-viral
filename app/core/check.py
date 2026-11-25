"""THE contract entry point (see CONTRACT.md). Owner: Lane A.

Mock mode works now, so Lane B can build against it from minute one.
The real pipeline is wired to stubs that Lane A fills in (PLAN.md steps A1–A3).
"""
import itertools
import json
import logging
import secrets

from app import config
from app.core import aletheia, fingerprint, normalize, store, verdict

log = logging.getLogger(__name__)

MOCK_NAMES = ["spliced_en", "fake_kn", "real_en", "fake_hi", "spliced_whatsapp", "fake_en"]
_cycle = itertools.cycle(MOCK_NAMES)


def new_id() -> str:
    return secrets.token_urlsafe(4)  # ~6 url-safe characters


def result_url(result_id: str) -> str:
    return f"{config.PUBLIC_BASE_URL}/r/{result_id}"


async def check(audio_path: str, *, source: dict) -> dict:
    """Check one clip. Never raises for a bad clip: returns band == "error" instead."""
    if config.MOCK_ALETHEIA:
        name = next(_cycle) if config.MOCK_ALETHEIA == "cycle" else config.MOCK_ALETHEIA
        return _mock_result(name)

    # ---- real pipeline: Lane A replaces the stubs step by step ----
    norm = await normalize.normalize(audio_path)                                    # A1
    cached = store.find(tg_file_unique_id=source.get("tg_file_unique_id"),          # A3
                        fp=fingerprint.compute(norm.path))
    if cached:
        return store.bump_times_checked(cached)
    raw = await aletheia.detect(norm.path, idempotency_key=norm.sha256)            # A1
    decided = verdict.decide(raw["result"])                                         # A2
    result = build_result(raw, decided, trimmed=norm.trimmed)
    store.save(result, source=source, fp=fingerprint.compute(norm.path))           # A3
    return result


async def send_feedback(operation_id: str, correct: bool, label: str | None = None) -> None:
    if config.MOCK_ALETHEIA or not operation_id:
        log.info("mock feedback: %s correct=%s label=%s", operation_id, correct, label)
        return
    await aletheia.feedback(operation_id, correct, label)                           # A3


def build_result(raw: dict, decided: dict, *, trimmed: bool = False, cache_hit: bool = False,
                 times_checked: int = 1, credits_charged: int | None = None) -> dict:
    """Shape an Aletheia REST response + verdict.decide() output into the CONTRACT dict."""
    r = raw["result"]
    overall_verdict = r.get("verdict") or ("fake" if r.get("is_synthetic") else "real")
    rid = new_id()
    model = raw.get("model") or {}
    return {
        "id": rid,
        "operation_id": raw.get("operation_id"),
        "model": f'{model.get("name", "aletheia")} {model.get("version", "")}'.strip(),
        "band": decided["band"],
        "overall": {"verdict": overall_verdict, "score": r.get("score")},
        "core_regions": decided.get("core_regions", []),
        "segments": r.get("segments", []),
        "duration": r.get("duration_seconds"),
        "scored_seconds": r.get("scored_seconds"),
        "trimmed": trimmed,
        "cache": {"hit": cache_hit, "times_checked": times_checked},
        "credits_charged": (raw.get("credits") or {}).get("charged", 0) if credits_charged is None else credits_charged,
        "error": None,
        "result_url": result_url(rid),
    }


def error_result(code: str, message: str) -> dict:
    rid = new_id()
    return {"id": rid, "operation_id": None, "model": "aletheia", "band": "error",
            "overall": {"verdict": None, "score": None}, "core_regions": [], "segments": [],
            "duration": None, "scored_seconds": None, "trimmed": False,
            "cache": {"hit": False, "times_checked": 1}, "credits_charged": 0,
            "error": {"code": code, "message": message}, "result_url": result_url(rid)}


def _mock_result(name: str) -> dict:
    if name.startswith("error_"):
        return error_result(name.removeprefix("error_"), f"mock {name}")
    path = config.FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        raise ValueError(f"MOCK_ALETHEIA={name!r}: no fixture {path.name}. Options: {MOCK_NAMES + ['cycle']}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))[name]
    return build_result(raw, expected, credits_charged=0)
