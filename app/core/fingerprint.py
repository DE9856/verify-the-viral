"""Lane A · step A3 — audio fingerprint for the "already checked" cache.

Tested (research/spikes/fp_test.py): Chromaprint `fpcalc -raw -json -length 300 <file>`, then
best (1 − bit error rate) over ±60 frame offsets. Re-encodes scored ≥ 0.89, different clips
≤ 0.71 → treat ≥ 0.80 as the same clip. Tier 1 before this: Telegram file_unique_id (exact).
"""


def compute(path: str) -> list[int]:
    raise NotImplementedError("Lane A · A3: fingerprint.compute()")


def similarity(a: list[int], b: list[int]) -> float:
    raise NotImplementedError("Lane A · A3: fingerprint.similarity()")
