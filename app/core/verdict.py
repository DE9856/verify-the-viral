"""Lane A · step A2 — turn Aletheia's result into one of four honest bands (PLAN.md §3).

Input: the "result" object of the API response. Output:
    {"band": "likely_fake" | "partly_fake" | "unclear" | "no_signs", "core_regions": [[start, end], ...]}

Rules (tested on research/results/, see tests/test_verdict.py):
- likely_fake : overall verdict is "fake"
- partly_fake : overall "real", and some seconds are covered by >= 2 overlapping fake segments.
                core_regions = those seconds, merged (spliced_en → [[10.0, 14.0]])
- unclear     : overall "real" and only isolated fake segments, OR scored_seconds < 10
- no_signs    : overall "real" and no fake segments
The overall "verdict" can be missing in MCP-shaped data: fall back to is_synthetic / label.
"""


def decide(result: dict) -> dict:
    raise NotImplementedError("Lane A · A2: verdict.decide()")
