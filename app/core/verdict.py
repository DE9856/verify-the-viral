"""Lane A · step A2 — turn Aletheia's result into one of four honest bands (PLAN.md §3).

Input: the "result" object of the API response. Output:
    {"band": "likely_fake" | "partly_fake" | "unclear" | "no_signs", "core_regions": [[start, end], ...]}

Rules (tested on the recorded results in app/fixtures/, see tests/test_verdict.py):
- likely_fake : overall verdict is "fake"
- partly_fake : overall "real", and some stretch is covered by >= 2 overlapping fake segments
                (segments are 4 s windows every 2 s, so a real fake sentence hits at least two).
                core_regions = those stretches, merged. spliced_en → [[10.0, 14.0]] (truth 10.0–14.8)
- unclear     : overall "real" and only isolated fake segments, OR less than 10 s was scored
- no_signs    : overall "real" and no fake segments
Computed with an exact sweep over segment boundaries (no time grid).

apply_edits(): when the clip is an edited copy of one we checked before (fpdiff.py found changed or
cut seconds), the diff is a second, independent signal:
- a changed stretch that ALSO has >= 1 fake segment on it becomes a core region (one window is not
  enough on its own, but two signals agreeing is) → partly_fake (unless already likely_fake)
- any other change or a cut: an edit is not proof of AI (people cut their own recordings), but the
  clip is never shown as a green all-clear: no_signs → unclear, reason "edited"
"""
from app import config

MIN_OVERLAP = 2
DEFAULT_THRESHOLD = 0.5   # only used for old results whose segments lack "verdict"


def overall_verdict(result: dict) -> str:
    v = result.get("verdict")
    if v in ("real", "fake"):
        return v
    if result.get("is_synthetic") is True or result.get("label") == "synthetic":
        return "fake"
    return "real"


def _is_fake(seg: dict, threshold: float) -> bool:
    v = seg.get("verdict")
    return v == "fake" if v in ("real", "fake") else seg.get("score", 0) >= threshold


def core_regions(segments: list[dict], threshold: float = DEFAULT_THRESHOLD, min_overlap: int = MIN_OVERLAP) -> list[list[float]]:
    fakes = [(float(s["start"]), float(s["end"])) for s in segments if _is_fake(s, threshold)]
    if len(fakes) < min_overlap:
        return []
    points = sorted({p for f in fakes for p in f})
    regions: list[list[float]] = []
    for a, b in zip(points, points[1:]):
        mid = (a + b) / 2
        if sum(s <= mid < e for s, e in fakes) >= min_overlap:
            if regions and abs(regions[-1][1] - a) < 1e-9:
                regions[-1][1] = b                      # extend the current region
            else:
                regions.append([a, b])
    return [[round(a, 2), round(b, 2)] for a, b in regions]


def decide(result: dict) -> dict:
    if overall_verdict(result) == "fake":
        return {"band": "likely_fake", "core_regions": []}
    segments = result.get("segments") or []
    threshold = result.get("threshold") or DEFAULT_THRESHOLD
    core = core_regions(segments, threshold)
    if core:
        return {"band": "partly_fake", "core_regions": core}
    any_fake = any(_is_fake(s, threshold) for s in segments)
    scored = result.get("scored_seconds") or result.get("duration_seconds") or 0
    if any_fake or scored < config.RELIABLE_SPEECH_SECONDS:
        return {"band": "unclear", "core_regions": []}
    return {"band": "no_signs", "core_regions": []}


EDIT_OVERLAP = 1.0   # seconds a fake segment must share with a changed stretch to back it up


def apply_edits(decided: dict, segments: list[dict], changed: list, removed: list,
                threshold: float = DEFAULT_THRESHOLD) -> dict:
    """decide()'s output adjusted for an edited copy (see the module docstring). Returns a new dict
    with "band", "core_regions" and, when the band was lowered for an edit, "reason": "edited"."""
    out = {"band": decided["band"], "core_regions": [list(r) for r in decided.get("core_regions", [])]}
    if out["band"] == "error":
        return out
    fakes = [(float(x["start"]), float(x["end"])) for x in segments if _is_fake(x, threshold)]
    unexplained = bool(removed)
    added = []
    for a, b in changed:
        covered = sum(max(0.0, min(b, e) - max(a, s)) for s, e in out["core_regions"])
        if covered >= 0.5 * (b - a):
            continue                                   # already inside a flagged region
        if any(min(b, e) - max(a, s) >= min(EDIT_OVERLAP, 0.5 * (b - a)) for s, e in fakes):
            added.append([round(a, 1), round(b, 1)])   # diff + detector agree
        else:
            unexplained = True
    if added and out["band"] != "likely_fake":
        out["band"] = "partly_fake"
        out["core_regions"] = _merge(out["core_regions"] + added)
    if unexplained and out["band"] == "no_signs":
        out["band"], out["reason"] = "unclear", "edited"
    return out


def _merge(regions: list[list[float]]) -> list[list[float]]:
    merged: list[list[float]] = []
    for a, b in sorted(regions):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged
