"""Fingerprint diff: which seconds of a clip differ from a stored one (like a text diff, for audio).

A whole-clip similarity is an average, so a few fake seconds inside a known clip get averaged away
(research/false-match.md: a same-length replacement of up to ~30 % still scored >= 0.80). The diff
instead lines the clips up piece by piece and reports every stretch that doesn't match:

  changed  seconds of the NEW clip found nowhere in the stored one (replaced or inserted audio)
  removed  seconds of the STORED clip missing from the new one, between matched parts (cut out)

Only a clip with nothing changed or removed is the same clip. Trims at either end are allowed.

How: Chromaprint gives one 32-bit code per ~0.124 s frame. Every new frame is compared with every
stored frame (bits in common), strong ~2 s diagonals give the candidate alignments ("anchors": one
for a plain copy, two or more around an insertion or a cut), and each new frame takes its best
anchor. Frames that fall well below the pair's own typical score (so heavy compression, which lowers
everything, doesn't count), in a run of at least mode.min_run, are a change. Resolution: edits of
~2 s or more; ~1 s edits are not seen (research/fp_diff.md)."""
from dataclasses import dataclass, field

import numpy as np

FRAME_S = 4096 / 3 / 11025       # Chromaprint hop: ~0.1238 s per fingerprint frame
WINDOW = 16                      # ~2 s: anchor search window
ANCHOR = 0.72                    # a window this good along one alignment makes it a candidate
MAX_ANCHORS = 6
JITTER = 2                       # also try anchors ±2 frames (drift after a speed undo)
EDGE = 6                         # ~0.75 s at the very start/end of the new clip may differ (padding)
NEAR = 0.65                      # whole-clip similarity worth diffing (different recordings scored <= 0.60;
                                 # a real clip vs itself with a sentence inserted 0.744)
REMOVED_EXTRA = 2                # a cut needs a slightly longer gap (undoing a speed change drifts ~3 frames)
TYPICAL_MIN = 0.75               # median frame score a same clip needs: true copies >= 0.869, half-replaced 0.59
MIN_SHARED = 0.5                 # below this share of matched frames it's a different clip, not an edit


@dataclass(frozen=True)
class Mode:
    smooth: int          # frames averaged per score
    drop: float          # a frame is unmatched when it scores this far below the pair's own median
    min_run: int         # unmatched frames in a row that make a change


# Calibrated on 122 true copies + 105 edits (research/fp_diff.md). A threshold relative to the pair's
# median, not a fixed one: heavy compression (clean recording -> 12-16 kbps Opus) lowers the whole
# clip and dips ~1 s at a time, while a fake stays low for its whole length. With these settings no
# true copy of any kind had a single unmatched frame; every edit of >= 2 s (direct, or edited and
# then sped up) had a run of >= 4. Edits of ~1 s are NOT seen (a fake that short looks like a dip).
DEFAULT = Mode(smooth=5, drop=0.24, min_run=3)

_POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


@dataclass
class Diff:
    verdict: str                                  # same | edited | different
    shared: float                                 # share of the new clip's frames that matched
    typical: float = 0.0                          # median frame score along the alignment
    changed: list[list[float]] = field(default_factory=list)   # [start, end] s in the new clip
    removed: list[list[float]] = field(default_factory=list)   # [start, end] s in the stored clip
    stray: float = 0.0                            # s of unmatched frames inside the clip too short to be a change

    @property
    def same(self) -> bool:
        return self.verdict == "same"


def _match_matrix(q: np.ndarray, s: np.ndarray) -> np.ndarray:
    """M[i, j] = share of bits frame i of q has in common with frame j of s (0.5 = chance)."""
    x = (q[:, None] ^ s[None, :]).astype(np.uint32)
    bits = _POP[x.view(np.uint8).reshape(len(q), len(s), 4)].sum(-1, dtype=np.uint16)
    return 1.0 - bits.astype(np.float32) / 32.0


def _moving_mean(v: np.ndarray, n: int) -> np.ndarray:
    if len(v) < n:
        return np.full(len(v), v.mean() if len(v) else 0.0, dtype=np.float32)
    c = np.cumsum(np.concatenate([[0.0], v]))
    m = (c[n:] - c[:-n]) / n                                   # windows starting at 0..len-n
    pad = n // 2
    return np.concatenate([np.full(pad, m[0]), m, np.full(len(v) - len(m) - pad, m[-1])]).astype(np.float32)


def _anchors(M: np.ndarray) -> list[int]:
    """Alignments k (stored frame = new frame + k) with a strong ~2 s stretch, best first."""
    nq, ns = M.shape
    scored = []
    for k in range(-(nq - WINDOW), ns - WINDOW + 1):
        d = np.diagonal(M, k)
        if len(d) < WINDOW:
            continue
        c = np.cumsum(np.concatenate([[0.0], d]))
        best = float(((c[WINDOW:] - c[:-WINDOW]) / WINDOW).max())
        if best >= ANCHOR:
            scored.append((best, k))
    picked: list[int] = []
    for _, k in sorted(scored, reverse=True):
        if all(abs(k - p) > JITTER for p in picked):
            picked.append(k)
        if len(picked) == MAX_ANCHORS:
            break
    return picked


def _sec(frames) -> float:
    """Frame index → seconds, as a plain float (numpy floats print as np.float64(…) in logs)."""
    return round(float(frames) * FRAME_S, 2)


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) index runs where mask is True."""
    edges = np.flatnonzero(np.diff(np.concatenate([[0], mask.astype(np.int8), [0]])))
    return list(zip(edges[::2], edges[1::2]))


def frame_scores(M: np.ndarray, anchors: list[int], smooth: int) -> tuple[np.ndarray, np.ndarray]:
    """For each new frame: best smoothed score over the anchors (±JITTER), and that anchor."""
    nq, ns = M.shape
    i = np.arange(nq)
    best = np.zeros(nq, dtype=np.float32)
    best_k = np.zeros(nq, dtype=np.int64)
    for k in sorted({k + j for k in anchors for j in range(-JITTER, JITTER + 1)}):
        j = i + k
        ok = (j >= 0) & (j < ns)
        v = np.where(ok, M[i, np.clip(j, 0, ns - 1)], 0.0).astype(np.float32)
        sm = np.where(ok, _moving_mean(v, smooth), 0.0)
        better = sm > best
        best[better], best_k[better] = sm[better], k
    return best, best_k


def diff(new_fp, stored_fp, mode: Mode = DEFAULT) -> Diff:
    q = np.asarray(new_fp, dtype=np.uint32)
    s = np.asarray(stored_fp, dtype=np.uint32)
    if len(q) < WINDOW or len(s) < WINDOW:
        return Diff("different", 0.0)
    M = _match_matrix(q, s)
    anchors = _anchors(M)
    if not anchors:
        return Diff("different", 0.0)
    best, best_k = frame_scores(M, anchors, mode.smooth)
    i = np.arange(len(q))
    typical = float(np.median(best))
    matched = best >= typical - mode.drop
    shared = float(matched.mean())
    if shared < MIN_SHARED:
        return Diff("different", round(float(shared), 3), round(float(typical), 3))

    changed, stray = [], 0
    for a, b in _runs(~matched):
        if b - a < mode.min_run:
            if 0 < a and b < len(q):                         # not codec padding at either end
                stray += b - a
            continue
        if (a == 0 or b == len(q)) and b - a <= EDGE:        # padding / codec edge at either end
            continue
        changed.append([_sec(a), _sec(b)])

    covered = np.zeros(len(s), dtype=bool)
    j = i[matched] + best_k[matched]
    covered[np.clip(j, 0, len(s) - 1)] = True
    covered = np.convolve(covered, np.ones(3), "same") > 0       # bridge single-frame gaps
    removed = []
    if covered.any():
        first, last = np.flatnonzero(covered)[[0, -1]]          # outside this = a trim: allowed
        for a, b in _runs(~covered[first:last + 1]):
            if b - a >= mode.min_run + REMOVED_EXTRA:
                removed.append([_sec(first + a), _sec(first + b)])
    if not changed and not removed and typical < TYPICAL_MIN:
        # nothing stands out because nothing matches well: when half a clip is replaced, the median
        # itself sinks into the fake's range. Not the same clip, whatever the runs say.
        return Diff("edited", round(float(shared), 3), round(float(typical), 3), [[0.0, _sec(len(q))]], [], _sec(stray))
    return Diff("edited" if changed or removed else "same", round(float(shared), 3), round(float(typical), 3),
                changed, removed, _sec(stray))
