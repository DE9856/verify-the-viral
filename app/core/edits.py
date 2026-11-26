"""Cheaper checks for an EDITED copy of a clip we already checked (credit trials, research/credit-trials.md).

When the fingerprint diff (fpdiff.py) says a clip is a known clip with some seconds changed or cut,
only those seconds are new audio. So instead of paying for the whole clip again:

  cut      only seconds REMOVED, nothing new          → 0 credits: the original's result, its times
                                                          moved to the new timeline, shown "edited"
  excerpt  ONE changed stretch (replaced in place / inserted)  → Aletheia checks ~10 s around it (min price:
                                                          20 credits for 10 s); the rest keeps the
                                                          original's result
  free     the original was 🔴 likely_fake            → 0 credits: at least half the clip is that AI audio
  full     anything else (several changes, a change + a cut, a long change) → whole clip, as before

Trial (real API, 2026-11-26): on 3 edited copies the 10 s excerpt gave the same answer as the
full check or better (it caught a 2 s AI insert the full check missed), 21 credits instead of ~50.
"""
from dataclasses import dataclass

from app.core import verdict

EXCERPT_SECONDS = 10.2     # >= config.RELIABLE_SPEECH_SECONDS; Aletheia bills >= 10 s anyway (min 20 credits)
CONTEXT = 1.5              # unchanged seconds kept on each side of the change
MAX_SHARE = 0.7            # an excerpt longer than this share of the clip: check the whole clip


@dataclass(frozen=True)
class Plan:
    mode: str                          # cut | excerpt | free | full
    start: float = 0.0                 # excerpt [start, end) in the NEW clip
    end: float = 0.0
    shift: float = 0.0                 # seconds the audio after the change moved (insert > 0)
    at: float = 0.0                    # where the change starts (same time in both clips)


def plan(original: dict, changed: list, removed: list, duration: float) -> Plan:
    if original.get("band") == "likely_fake":
        return Plan("free")
    if original.get("band") not in ("partly_fake", "unclear", "no_signs"):
        return Plan("full")
    if removed and not changed:
        return Plan("cut")
    if len(changed) == 1 and _in_place(changed[0], removed):
        a, b = changed[0]
        lo, hi = max(0.0, a - CONTEXT), min(duration, b + CONTEXT)
        if hi - lo < EXCERPT_SECONDS:                     # pad to the length we pay for anyway
            mid = (lo + hi) / 2
            lo = max(0.0, min(mid - EXCERPT_SECONDS / 2, duration - EXCERPT_SECONDS))
            hi = min(duration, lo + EXCERPT_SECONDS)
        if hi - lo <= MAX_SHARE * duration:
            return Plan("excerpt", round(lo, 2), round(hi, 2),
                        shift=round(duration - float(original.get("duration") or duration), 2), at=float(a))
    return Plan("full")


def _in_place(change: list, removed: list) -> bool:
    """An insert (nothing removed) or a replacement (the one removed stretch sits where the change is)."""
    if not removed:
        return True
    if len(removed) > 1:
        return False
    (a, b), (x, y) = change, removed[0]
    return x < b + 1.5 and y > a - 1.5


# --------------------------------------------------------------------------- timeline mapping

def map_cut(t: float, removed: list) -> float:
    """Original time → time in the copy with `removed` ([start, end] in the original) cut out."""
    out = t
    for a, b in removed:
        if t >= b:
            out -= b - a
        elif t > a:
            out -= t - a
    return round(out, 2)


def map_shift(t: float, at: float, shift: float) -> float:
    """Original time → new time when audio after `at` moved by `shift` seconds."""
    return round(t + shift if t >= at else t, 2)


def _outside(items: list[list[float]], lo: float, hi: float) -> list[list[float]]:
    """Parts of [a, b] stretches outside [lo, hi)."""
    out = []
    for a, b in items:
        for x, y in ((a, min(b, lo)), (max(a, hi), b)):
            if y - x > 0.05:
                out.append([round(x, 2), round(y, 2)])
    return out


def _seg(s: dict, a: float, b: float) -> dict:
    return {**s, "start": round(a, 3), "end": round(b, 3)}


def merge_cut(original: dict, removed: list) -> dict:
    """The original's result on the cut copy's timeline (windows across a cut are dropped)."""
    segs = [_seg(s, map_cut(s["start"], removed), map_cut(s["end"], removed))
            for s in original.get("segments") or []
            if not any(s["start"] < b and s["end"] > a for a, b in removed)]
    regions = [[map_cut(a, removed), map_cut(b, removed)] for a, b in original.get("core_regions") or []]
    regions = [r for r in regions if r[1] - r[0] > 0.05]
    band = original["band"] if regions or original["band"] != "partly_fake" else "unclear"
    decided = verdict.apply_edits({"band": band, "core_regions": regions}, [], [], removed)
    return {"segments": segs, **decided}


def merge_excerpt(original: dict, p: Plan, excerpt_result: dict, changed: list) -> dict:
    """The original's result for the unchanged seconds + the excerpt's for the re-checked ones."""
    m = lambda t: map_shift(t, p.at, p.shift)                       # noqa: E731
    threshold = excerpt_result.get("threshold") or verdict.DEFAULT_THRESHOLD
    old = [_seg(s, m(s["start"]), m(s["end"])) for s in original.get("segments") or []]
    old = [s for s in old if s["end"] <= p.start or s["start"] >= p.end]
    new = [_seg(s, s["start"] + p.start, min(s["end"] + p.start, p.end)) for s in excerpt_result.get("segments") or []]
    regions = _outside([[m(a), m(b)] for a, b in original.get("core_regions") or []], p.start, p.end)
    regions += verdict.core_regions(new, threshold)
    band = "partly_fake" if regions else ("unclear" if original["band"] == "partly_fake" else original["band"])
    decided = verdict.apply_edits({"band": band, "core_regions": verdict._merge(regions)}, new, changed, [], threshold)
    return {"segments": sorted(old + new, key=lambda s: s["start"]), **decided}
