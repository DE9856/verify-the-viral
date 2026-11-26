"""Cheaper checks for an EDITED copy of a clip we already checked (credit trials, research/credit-trials.md).

When the fingerprint diff (fpdiff.py) says a clip is a known clip with some seconds changed or cut,
only those seconds are new audio. So instead of paying for the whole clip again:

  excerpt  ONE changed stretch (replaced in place / inserted), or ONE cut → Aletheia checks ~10 s
           around it (min price: 20 credits for 10 s), so a small AI piece slipped in at the edit is
           still heard; the rest keeps the original's result, its times moved to the new timeline
  free     the original was 🔴 likely_fake            → 0 credits: most of the clip is that AI audio
  full     anything else (several changes, a change + a cut, a long change), or a MESSY diff
           → whole clip, as before

Safety (2026-11-26): the cheap modes run only on a CLEAN diff: the copy otherwise matches almost
perfectly (`typical` >= CLEAN_TYPICAL) and has no stray unmatched frames inside it (`stray` <=
CLEAN_STRAY s: bits too short to be reported as a change, where a hidden small edit would show).
A messy diff always gets the whole-clip check. A cut is checked
around the cut point instead of being free, for the same reason.

Trial (real API, 2026-11-26): on 3 edited copies the 10 s excerpt gave the same answer as the
full check or better (it caught a 2 s AI insert the full check missed), 21 credits instead of ~50.
"""
from dataclasses import dataclass

from app.core import verdict

EXCERPT_SECONDS = 10.2     # >= config.RELIABLE_SPEECH_SECONDS; Aletheia bills >= 10 s anyway (min 20 credits)
CONTEXT = 1.5              # unchanged seconds kept on each side of the change
MAX_SHARE = 0.7            # an excerpt longer than this share of the clip: check the whole clip
CLEAN_TYPICAL = 0.90       # median frame score along the alignment (edited test copies: 0.994-1.0)
CLEAN_STRAY = 0.3          # s of stray unmatched frames allowed (clean edits and true re-encodes: 0.0)


@dataclass(frozen=True)
class Plan:
    mode: str                          # excerpt | free | full
    start: float = 0.0                 # excerpt [start, end) in the NEW clip
    end: float = 0.0
    shift: float = 0.0                 # seconds the audio after the change moved (insert > 0)
    at: float = 0.0                    # where the change starts (same time in both clips)
    cut: bool = False                  # the excerpt is around a cut (times map with map_cut)


def clean(typical: float, stray: float) -> bool:
    """Outside the reported changes the copy matches almost perfectly, with nothing left unexplained."""
    return typical >= CLEAN_TYPICAL and stray <= CLEAN_STRAY


def _window(a: float, b: float, duration: float) -> tuple[float, float]:
    lo, hi = max(0.0, a - CONTEXT), min(duration, b + CONTEXT)
    if hi - lo < EXCERPT_SECONDS:                         # pad to the length we pay for anyway
        mid = (lo + hi) / 2
        lo = max(0.0, min(mid - EXCERPT_SECONDS / 2, duration - EXCERPT_SECONDS))
        hi = min(duration, lo + EXCERPT_SECONDS)
    return round(lo, 2), round(hi, 2)


def plan(original: dict, changed: list, removed: list, duration: float,
         typical: float = 1.0, stray: float = 0.0) -> Plan:
    if original.get("band") not in ("likely_fake", "partly_fake", "unclear", "no_signs"):
        return Plan("full")
    if not clean(typical, stray):
        return Plan("full")
    if original["band"] == "likely_fake":
        return Plan("free")
    if removed and not changed and len(removed) == 1:
        at = removed[0][0]                                # the cut point, same time in both clips
        lo, hi = _window(at, at, duration)
        if hi - lo <= MAX_SHARE * duration:
            return Plan("excerpt", lo, hi, at=at, cut=True)
    if len(changed) == 1 and _in_place(changed[0], removed):
        a, b = changed[0]
        lo, hi = _window(a, b, duration)
        if hi - lo <= MAX_SHARE * duration:
            return Plan("excerpt", lo, hi,
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


def merge_excerpt(original: dict, p: Plan, excerpt_result: dict, changed: list,
                  removed: list | None = None) -> dict:
    """The original's result for the unchanged seconds + the excerpt's for the re-checked ones."""
    removed = removed or []
    if p.cut:
        m = lambda t: map_cut(t, removed)                           # noqa: E731
    else:
        m = lambda t: map_shift(t, p.at, p.shift)                   # noqa: E731
    threshold = excerpt_result.get("threshold") or verdict.DEFAULT_THRESHOLD
    old = [_seg(s, m(s["start"]), m(s["end"])) for s in original.get("segments") or []]
    old = [s for s in old if s["end"] <= p.start or s["start"] >= p.end]
    new = [_seg(s, s["start"] + p.start, min(s["end"] + p.start, p.end)) for s in excerpt_result.get("segments") or []]
    # the original's AI regions stay valid for audio that wasn't edited, even inside the excerpt: drop
    # them only where the audio changed (a cut removes nothing that is still in the copy)
    regions = [[m(a), m(b)] for a, b in original.get("core_regions") or []]
    for lo, hi in ([] if p.cut else changed):
        regions = _outside(regions, lo, hi)
    regions = [r for r in regions if r[1] - r[0] > 0.05]
    regions += verdict.core_regions(new, threshold)
    band = "partly_fake" if regions else ("unclear" if original["band"] == "partly_fake" else original["band"])
    decided = verdict.apply_edits({"band": band, "core_regions": verdict._merge(regions)}, new, changed,
                                  removed if p.cut else [], threshold)
    return {"segments": sorted(old + new, key=lambda s: s["start"]), **decided}
