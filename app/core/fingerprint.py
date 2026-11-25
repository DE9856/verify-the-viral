"""Audio fingerprint for the "already checked" cache (layer 4 in check.py; layer 3 is the exact
decoded-audio hash in normalize.py).

Tested (research/spikes/fp_test.py): Chromaprint `fpcalc -raw -json -length 300 <file>`, then best
(1 − bit error rate) over ±60 frame offsets (~±7 s). Re-encodes (Opus 16k, Opus ×2, MP3 64k,
AAC-from-MP4, −6 dB, 1.3 s trim) scored ≥ 0.89; different clips ≤ 0.71 → SAME_CLIP = 0.80.

If fpcalc isn't installed, compute() returns None and only the exact cache tiers work.
"""
import json
import logging
import os
import shutil
import subprocess
from functools import lru_cache

import numpy as np

from app import config

log = logging.getLogger(__name__)
SAME_CLIP = 0.80
MAX_OFFSET = 60        # frames of ~0.124 s
MIN_OVERLAP = 20


@lru_cache(maxsize=1)
def fpcalc_path() -> str | None:
    candidates = [config.FPCALC_PATH]
    if not os.path.isabs(config.FPCALC_PATH):
        candidates.insert(0, str(config.ROOT / config.FPCALC_PATH))
    # then the repo's bin/ (Windows download) and plain `fpcalc` on PATH (Linux: dnf/apt package),
    # so an env copied from another machine still finds it
    candidates += [str(config.ROOT / "bin" / "fpcalc.exe"), str(config.ROOT / "bin" / "fpcalc"), "fpcalc"]
    for c in candidates:
        if os.path.isfile(c):
            return c
        found = shutil.which(c)
        if found:
            return found
    log.warning("fpcalc not found (FPCALC_PATH=%s): fingerprint cache tier disabled", config.FPCALC_PATH)
    return None


def compute(path: str) -> list[int] | None:
    exe = fpcalc_path()
    if not exe:
        return None
    try:  # best effort: a fingerprint failure only means "no fuzzy cache for this clip"
        r = subprocess.run([exe, "-raw", "-json", "-length", str(config.MAX_SECONDS), path],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            log.warning("fpcalc failed on %s: %s", path, r.stderr.strip()[:200])
            return None
        return json.loads(r.stdout)["fingerprint"] or None
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as e:
        log.warning("fpcalc unusable on %s: %s", path, e)
        return None


def similarity(a: list[int] | np.ndarray, b: list[int] | np.ndarray) -> float:
    """1.0 = identical. Partial overlaps are pulled toward 0.5 (chance), so a clip that only shares
    its first 10 s with another doesn't count as the same clip."""
    x = np.asarray(a, dtype=np.uint32)
    y = np.asarray(b, dtype=np.uint32)
    if not len(x) or not len(y):
        return 0.0
    longest, best = max(len(x), len(y)), 0.0
    for off in range(-MAX_OFFSET, MAX_OFFSET + 1):
        u, v = (x[off:], y) if off >= 0 else (x, y[-off:])
        n = min(len(u), len(v))
        if n < MIN_OVERLAP:
            continue
        bit_errors = np.unpackbits((u[:n] ^ v[:n]).view(np.uint8)).sum()
        match = 1 - bit_errors / (n * 32)
        cover = n / longest
        best = max(best, match * cover + 0.5 * (1 - cover))
    return float(best)
