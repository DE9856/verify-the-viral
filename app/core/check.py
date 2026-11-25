"""THE contract entry point (see CONTRACT.md).

Pipeline, cheapest step first (layers of "have we checked this clip before?"):
  1. Telegram file_unique_id already seen?            → cached result, no decoding at all
  2. normalize (passthrough / stream copy / transcode) → sha256 of the bytes we'd send
     same bytes already checked?                       → cached result
  3. same decoded audio already checked?               → cached result (other container / lossless
     format / renamed file: .ogg vs .opus, WAV vs FLAC, voice note inside a video)
  4. a stored clip of similar length? fingerprint it   → cached result if similarity >= 0.80 AND
     the fingerprint diff (fpdiff.py) finds no changed or cut seconds; if it does, the clip is an
     edited copy: checked by the API like a new clip, with result["edited_copy_of"] saying which
     (lossy re-encodes: WhatsApp Opus, MP3, AAC; needs fpcalc)
  5. a copy at another speed or pitch of a stored clip? → cached result, cache.variant says how
     (variants.py: undo the change with ffmpeg, fingerprint again; only runs when 1-4 missed)
     (no stored clip from half to double the length: skip 4-5 and fingerprint in parallel
      with the API call)
  6. Aletheia REST call (Idempotency-Key = sha256)     → verdict bands → store
Identical clips arriving at the same moment share one API call (single-flight).
Mock mode (MOCK_ALETHEIA) replays recorded real results and also stores them, so result links work.
"""
import asyncio
import itertools
import json
import logging
import secrets
import time
from pathlib import Path

from app import config
from app.core import aletheia, fingerprint, normalize, store, variants, verdict
from app.core.aletheia import AletheiaError
from app.core.normalize import NormalizeError

log = logging.getLogger(__name__)

MOCK_NAMES = ["spliced_en", "fake_kn", "real_en", "fake_hi", "spliced_whatsapp", "fake_en"]
_cycle = itertools.cycle(MOCK_NAMES)
_inflight: dict[str, asyncio.Future] = {}

# Aletheia / normalize error codes → the few codes in CONTRACT.md
ERROR_MAP = {
    "insufficient_speech": "insufficient_speech", "audio_too_short": "insufficient_speech",
    "silent_audio": "insufficient_speech", "no_audio": "insufficient_speech",
    "insufficient_credits": "out_of_credits",
    "file_too_large": "too_large", "too_large": "too_large",
}


def new_id() -> str:
    return secrets.token_urlsafe(4)  # ~6 url-safe characters


def result_url(result_id: str) -> str:
    return f"{config.PUBLIC_BASE_URL}/r/{result_id}"


# --------------------------------------------------------------------------- public API

async def check(audio_path: str, *, source: dict) -> dict:
    """Check one clip. Never raises for a bad clip: returns band == "error" instead."""
    t0 = time.perf_counter()
    if config.MOCK_ALETHEIA:
        name = next(_cycle) if config.MOCK_ALETHEIA == "cycle" else config.MOCK_ALETHEIA
        return _mock_result(name, source)
    tg = source.get("tg_file_unique_id")
    try:
        if tg and (cid := store.find_exact(tg_file_unique_id=tg)):
            return _done(store.hit(cid, source=source), "cache:telegram", t0)
        if tg:
            return await _once(f"tg:{tg}", lambda: _check_file(audio_path, source, t0), source)
        return await _check_file(audio_path, source, t0)
    except NormalizeError as e:
        return _done(_save_error(ERROR_MAP.get(e.code, "failed"), str(e), source), f"error:{e.code}", t0)
    except AletheiaError as e:
        return _done(_save_error(ERROR_MAP.get(e.code, "failed"), e.message, source), f"error:{e.code}", t0)
    except Exception as e:  # noqa: BLE001 — a bad clip must never crash the bot
        log.exception("check failed")
        return _done(_save_error("failed", type(e).__name__, source), "error:exception", t0)


async def send_feedback(operation_id: str, correct: bool, label: str | None = None) -> None:
    """CONTRACT §2 (used by the bot's 👍/👎). Stores the answer and forwards it to DetectifAI."""
    check_id = store.check_id_for_operation(operation_id) if operation_id else None
    await record_feedback(check_id, correct, label, channel="telegram", operation_id=operation_id)


async def record_feedback(check_id: str | None, correct: bool, label: str | None = None, *,
                          channel: str | None = None, operation_id: str | None = None) -> None:
    """Also used by the result page. Never raises: feedback must not break a reply."""
    operation_id = operation_id or (store.operation_id_for(check_id) if check_id else None)
    try:
        if check_id:
            store.add_feedback(check_id, operation_id, correct, label, channel)
        if operation_id and not config.MOCK_ALETHEIA:
            await aletheia.feedback(operation_id, correct, label)
        else:
            log.info("feedback stored locally only (mock or no operation_id): %s %s", check_id, correct)
    except Exception:  # noqa: BLE001
        log.exception("feedback failed for %s", check_id)


# --------------------------------------------------------------------------- pipeline

async def _check_file(audio_path: str, source: dict, t0: float) -> dict:
    norm = await normalize.normalize(audio_path)
    tg = source.get("tg_file_unique_id")
    if cid := store.find_exact(sha256=norm.sha256):
        return _done(store.hit(cid, tg_file_unique_id=tg, source=source), "cache:exact", t0, norm)
    if norm.pcm_sha256 and (cid := store.find_exact(pcm_sha256=norm.pcm_sha256)):
        return _done(store.hit(cid, tg_file_unique_id=tg, source=source), "cache:decoded", t0, norm)
    return await _once(f"sha:{norm.sha256}", lambda: _check_normalized(norm, source, t0), source)


async def _check_normalized(norm: normalize.Normalized, source: dict, t0: float) -> dict:
    tg = source.get("tg_file_unique_id")
    edited = None
    if store.has_candidates(norm.duration, *variants.window(norm.duration)):
        fp = await asyncio.to_thread(fingerprint.compute, norm.path)
        match, edited = await asyncio.to_thread(store.match_fingerprint, fp, norm.duration)
        if match:
            return _done(store.hit(match[0], tg_file_unique_id=tg, source=source), f"cache:fingerprint({match[1]:.2f})", t0, norm)
        if v := await asyncio.to_thread(variants.find, norm.path, fp, norm.duration):
            # no tg_file_unique_id: a re-forward of this copy should get the same "copy of" note,
            # which only this layer can give (it's free either way)
            r = store.hit(v.check_id, source=source)
            r["cache"]["variant"] = v.as_cache_info()
            return _done(r, f"cache:{v.kind}({v.score:.2f}, speed={v.speed}, semitones={v.semitones})", t0, norm)
        if edited:  # parts match a known clip but some seconds differ: never reuse its verdict
            log.info("edited copy of %s: changed %s, removed %s", edited[0], edited[1].changed, edited[1].removed)
        raw = await aletheia.detect(norm.path, idempotency_key=norm.sha256)
    else:
        raw, fp = await asyncio.gather(aletheia.detect(norm.path, idempotency_key=norm.sha256),
                                       asyncio.to_thread(fingerprint.compute, norm.path))
    result = build_result(raw, verdict.decide(raw["result"]), trimmed=norm.trimmed)
    if edited:
        cid, d = edited
        result["edited_copy_of"] = {"id": cid, "result_url": result_url(cid), "changed": d.changed,
                                    "removed": d.removed}
    store.save(result, source=source, sha256=norm.sha256, fp=fp, duration=norm.duration, audio_path=norm.path,
               pcm_sha256=norm.pcm_sha256)
    return _done(result, "api", t0, norm)


async def _once(key: str, fn, source: dict) -> dict:
    """Single-flight: concurrent identical work waits for the first run, then counts as a cache hit."""
    if key in _inflight:
        first = await asyncio.shield(_inflight[key])
        if first["band"] == "error":
            return first
        return store.hit(first["id"], tg_file_unique_id=source.get("tg_file_unique_id"), source=source)
    fut = asyncio.get_running_loop().create_future()
    _inflight[key] = fut
    try:
        result = await fn()
        fut.set_result(result)
        return result
    except BaseException as e:
        fut.set_exception(e)
        fut.exception()  # mark retrieved so asyncio doesn't warn when nobody else was waiting
        raise
    finally:
        _inflight.pop(key, None)


# --------------------------------------------------------------------------- result shaping

def build_result(raw: dict, decided: dict, *, trimmed: bool = False, cache_hit: bool = False,
                 times_checked: int = 1, credits_charged: int | None = None) -> dict:
    """Shape an Aletheia REST response + verdict.decide() output into the CONTRACT dict."""
    r = raw["result"]
    rid = new_id()
    model = raw.get("model") or {}
    return {
        "id": rid,
        "operation_id": raw.get("operation_id"),
        "model": f'{model.get("name", "aletheia")} {model.get("version", "")}'.strip(),
        "band": decided["band"],
        "overall": {"verdict": verdict.overall_verdict(r), "score": r.get("score")},
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


def _save_error(code: str, message: str, source: dict) -> dict:
    r = error_result(code, message)
    try:
        store.save(r, source=source, sha256=None, fp=None, duration=None, audio_path=None)
    except Exception:  # noqa: BLE001 — the reply matters more than the record
        log.exception("could not store error result")
    return r


def _done(result: dict, how: str, t0: float, norm: normalize.Normalized | None = None) -> dict:
    log.info("check %s band=%s via=%s norm=%s credits=%s %.0fms", result["id"], result["band"], how,
             norm.method if norm else "-", result.get("credits_charged"), 1000 * (time.perf_counter() - t0))
    return result


def _mock_result(name: str, source: dict) -> dict:
    if name.startswith("error_"):
        return error_result(name.removeprefix("error_"), f"mock {name}")
    path = config.FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        raise ValueError(f"MOCK_ALETHEIA={name!r}: no fixture {path.name}. Options: {MOCK_NAMES + ['cycle']}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))[name]
    result = build_result(raw, expected, credits_charged=0)
    audio = next(iter(sorted((config.ROOT / "research" / "test-audio").glob(f"{name}.*"))), None)
    try:  # store it so /r/<id> works in mock mode too; the waveform is the fixture's real audio
        store.save(result, source=source, sha256=None, fp=None, duration=result["duration"],
                   audio_path=str(audio) if audio else None)
    except Exception:  # noqa: BLE001
        log.exception("mock: could not store result")
    return result
