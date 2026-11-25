"""Layer 5 of the "already checked" cache: a copy of a stored clip at another speed or pitch.

Runs only when every cheaper layer missed (Telegram id, file sha, decoded-audio sha, plain
fingerprint). Three kinds of copy, all matched the same way: undo the change with ffmpeg, then
fingerprint again and compare with the usual rule (similarity >= fingerprint.SAME_CLIP = 0.80).

  speed  faster/slower, pitch kept (playback speed, sped-up reels)   ffmpeg atempo
  tape   faster+higher / slower+deeper together (nightcore, slowed)  ffmpeg asetrate
  pitch  higher/deeper voice, same length (voice changers)           asetrate + atempo

Speed and tape copies: the length tells the speed (stored length / new length). Speed copies are
pre-screened in ~1 ms each by stretching the stored fingerprint (no audio work), which also finds
the speed when the copy was trimmed; only those that pass are undone with ffmpeg. Tape copies
can't be pre-screened (stretching a fingerprint can't undo a pitch change), so the length ratio is
tried directly, for the most-checked clips first, up to MAX_TAPE_TRIES.
Pitch copies keep their length, so nothing tells the shift: whole semitones -6..+6 are undone in
parallel, then half-steps next to the best one if it came close.

A match must also pass the fingerprint diff (fpdiff.py): an edited and sped-up copy is not the
original. It sees edits of ~2 s or more, also after a speed undo (research/fp_diff.md).

Evidence (research/speed-test.md, 0 credits): speed 0.5-2x >= 0.84, tape 0.95-0.99, pitch
-4..+4 semitones (incl. 0.5, 2.5, 3.3) 0.86-0.97; different clips <= 0.67 across every attempt.
"""
import logging
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import numpy as np

from app.core import fingerprint, fpdiff, store
from app.core.normalize import FFMPEG

log = logging.getLogger(__name__)

MIN_SPEED, MAX_SPEED = 0.5, 2.0
SAME_LENGTH = 0.03          # |ratio - 1| below this: same length, so only a pitch shift is possible
GATE = 0.62                 # pre-screen score for speed copies (all passed; 1 of 64 different pairs did)
SWEEP = 0.02                # speed steps of the pre-screen sweep
MAX_TEMPO_TRIES = 6         # ffmpeg undo runs for speed copies (best pre-screen scores first)
MAX_TAPE_TRIES = 8          # ffmpeg undo runs for tape copies (most-checked clips first)
SEMITONES = [s for s in range(-6, 7) if s]
REFINE_FROM = 0.70          # a pitch try this close gets half-semitone neighbours tried too
WORKERS = min(8, os.cpu_count() or 2)


@dataclass
class Match:
    check_id: str
    score: float
    kind: str                   # speed | tape | pitch
    speed: float | None = None  # how much faster the copy plays than the stored clip
    semitones: float | None = None  # how far the copy's pitch was moved

    def as_cache_info(self) -> dict:
        d = asdict(self)
        d.pop("check_id")
        d["score"] = round(self.score, 3)
        return d


def window(duration: float) -> tuple[float, float]:
    """Lengths a stored clip can have for this clip to be a speed copy of it."""
    return duration * MIN_SPEED * 0.97, duration * MAX_SPEED * 1.03


def find(path: str, fp: list[int] | None, duration: float) -> Match | None:
    """Best stored clip this one is a speed / tape / pitch copy of, or None. Best effort: never raises."""
    if not fp or not duration or not fingerprint.fpcalc_path():
        return None
    t0 = time.perf_counter()
    try:
        cands = store.fp_candidates(*window(duration))
        if not cands:
            return None
        q = np.asarray(fp, dtype=np.uint32)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp, ThreadPoolExecutor(WORKERS) as pool:
            undo = _Undo(path, tmp, pool)
            m = _speed_or_tape(q, duration, cands, undo) or _pitch(duration, cands, undo)
        log.info("variants: %s in %.0f ms (%d candidates, %d ffmpeg runs)",
                 f"{m.kind} match {m.check_id} ({m.score:.2f})" if m else "no match",
                 1000 * (time.perf_counter() - t0), len(cands), undo.runs)
        return m
    except Exception:  # noqa: BLE001 — a failed lookup only means "check it with the API"
        log.exception("variant lookup failed")
        return None


# --------------------------------------------------------------------------- speed and tape

def _stretch(f: np.ndarray, speed: float, n: int) -> np.ndarray:
    """Stored fingerprint f as a copy played `speed` times faster would look (n frames)."""
    idx = np.round(np.arange(n) * speed).astype(int)
    return f[idx[idx < len(f)]]


def _speed_or_tape(q, duration, cands, undo) -> Match | None:
    tempo, tape = [], []
    for cid, f, d, _times in cands:
        ratio = d / duration
        if abs(ratio - 1) < SAME_LENGTH or not (MIN_SPEED * 0.97 <= ratio <= MAX_SPEED * 1.03):
            continue
        sf = np.asarray(f, dtype=np.uint32)
        # pre-screen: sweep speeds around the length ratio (a trimmed copy makes the ratio too high,
        # a trimmed original too low), then refine around the best
        grid = np.arange(max(MIN_SPEED * 0.96, ratio * 0.8), min(MAX_SPEED * 1.04, ratio * 1.25) + 1e-9, SWEEP)
        score, best = max((fingerprint.similarity(q, _stretch(sf, s, len(q))), s) for s in grid)
        if score >= GATE:
            fine = np.arange(best - SWEEP, best + SWEEP + 1e-9, SWEEP / 4)
            score, best = max((fingerprint.similarity(q, _stretch(sf, s, len(q))), s) for s in fine)
            tempo.append((score, cid, sf, float(best), ratio))
        tape.append((cid, sf, ratio))
    tries = []
    for _score, cid, sf, best, ratio in sorted(tempo, key=lambda t: t[0], reverse=True)[:MAX_TEMPO_TRIES]:
        tries += [(cid, sf, "speed", best), (cid, sf, "speed", ratio)]
    tries += [(cid, sf, "tape", ratio) for cid, sf, ratio in tape[:MAX_TAPE_TRIES]]
    if not tries:
        return None
    for cid, sf, kind, s in tries:      # start every ffmpeg run at once
        undo.start(kind, s)
    best = None
    for cid, sf, kind, s in tries:
        fq = undo.result(kind, s)
        if fq:
            sc = fingerprint.similarity(fq, sf)
            if sc >= fingerprint.SAME_CLIP and (best is None or sc > best.score) and _unchanged(fq, sf):
                best = Match(cid, sc, kind, speed=round(s, 2))
    return best


# --------------------------------------------------------------------------- pitch

def _pitch(duration, cands, undo) -> Match | None:
    same = [(cid, np.asarray(f, dtype=np.uint32)) for cid, f, d, _ in cands if abs(d / duration - 1) < SAME_LENGTH]
    if not same:
        return None

    def best_of(shifts):
        for u in shifts:
            undo.start("pitch", u)
        out = None
        for u in shifts:
            fq = undo.result("pitch", u)
            for cid, sf in same if fq else ():
                sc = fingerprint.similarity(fq, sf)
                if out is None or sc > out[0]:
                    out = (sc, cid, u, fq, sf)
        return out

    found = best_of(SEMITONES)
    if found and REFINE_FROM <= found[0] < fingerprint.SAME_CLIP:
        found = max(found, best_of([found[2] - 0.5, found[2] + 0.5]) or found, key=lambda t: t[0])
    if found and found[0] >= fingerprint.SAME_CLIP and _unchanged(found[3], found[4]):
        # we undid a shift of u semitones, so the copy was shifted by -u
        return Match(found[1], found[0], "pitch", semitones=-found[2])
    return None


def _unchanged(fq, sf) -> bool:
    """The undone copy must also pass the fingerprint diff, so an edited AND sped-up copy isn't
    taken for the original. Sees edits of >= ~2 s."""
    return fpdiff.diff(fq, sf).same


# --------------------------------------------------------------------------- ffmpeg undo runs

class _Undo:
    """Fingerprints of the new clip with a speed or pitch change undone; each one computed once,
    in parallel on a thread pool (ffmpeg and fpcalc are separate processes)."""

    def __init__(self, path: str, tmp: str, pool: ThreadPoolExecutor):
        self.path, self.tmp, self.pool, self.jobs, self.runs = path, tmp, pool, {}, 0

    def start(self, kind: str, value: float) -> None:
        key = (kind, round(value, 3))
        if key not in self.jobs:
            self.runs += 1
            self.jobs[key] = self.pool.submit(self._run, kind, key[1])

    def result(self, kind: str, value: float) -> list[int] | None:
        self.start(kind, value)
        return self.jobs[(kind, round(value, 3))].result()

    def _run(self, kind: str, value: float) -> list[int] | None:
        out = os.path.join(self.tmp, f"{kind}_{value:+.3f}.wav")
        r = subprocess.run([FFMPEG, "-v", "error", "-y", "-i", self.path, "-vn", "-ac", "1",
                            "-filter:a", _filter(kind, value), out], capture_output=True)
        return fingerprint.compute(out) if r.returncode == 0 else None


def _atempo(t: float) -> str:
    """atempo accepts 0.5..100 per filter: chain them for bigger slow-downs."""
    parts = []
    while t < 0.5:
        parts.append("atempo=0.5")
        t /= 0.5
    return ",".join(parts + [f"atempo={t:.6f}"])


def _filter(kind: str, value: float) -> str:
    if kind == "speed":       # copy plays `value` times faster with pitch kept: slow it back down
        return _atempo(1 / value)
    if kind == "tape":        # copy plays `value` times faster and higher: resample it back
        return f"aresample=44100,asetrate={44100 / value:.3f},aresample=44100"
    r = 2 ** (value / 12)     # pitch: move pitch by `value` semitones, keep the length
    return f"aresample=44100,asetrate={44100 * r:.3f},aresample=44100,{_atempo(1 / r)}"
