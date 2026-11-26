"""Do 10 s excerpts of REAL voices false-alarm? (edits.py checks ~10 s excerpts of edited copies)

    MOCK_ALETHEIA= PYTHONPATH=. python research/spikes/excerpt_false_alarm.py
Excerpts aimed at the hottest windows of our real recordings (research/real-world.md); pass = no
fake window pair (no core region) and overall real. Logged to research/results/credit_trials.jsonl.
"""
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from credit_trials import BUDGET, EXCERPT, LEDGER, OUT, RESERVE, WA, excerpt, spent, summary  # noqa: E402

from app.core import aletheia  # noqa: E402

CASES = [("real_hi", 27.0), ("real_hi", 38.0), ("notice_hi", 9.0), ("real_kn", 16.0), ("notice_kn", 0.0), ("real_en", 11.0)]


async def main():
    bal = (await aletheia.credits())["available"]
    est = 21 * len(CASES)
    if spent() + est > BUDGET or bal - est < RESERVE:
        sys.exit(f"REFUSED: budget ({spent()}+{est}) or reserve ({bal})")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, start in CASES:
        p = OUT / f"T4_{name}_{start:g}s_excerpt.wav"
        excerpt(WA / f"{name}.ogg", p, start)
        raw = await aletheia.detect(str(p), idempotency_key="trial-" + hashlib.sha256(p.read_bytes()).hexdigest())
        row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "trial": f"T4_{name}_{start:g}", "idea": "real-voice excerpt false alarm",
               "file": p.name, "file_seconds": EXCERPT, "charged": (raw.get("credits") or {}).get("charged", 0),
               "question": f"10 s excerpt of {name} from {start:g} s: still real?", "baseline": "full clip: real, 0 fake windows",
               **summary(raw["result"])}
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        print(f"{row['trial']:18} charged {row['charged']:3} {row['overall']} {row['score']:.3f} band {row['band']} fake {row['fake_windows']} top {row['top_score']}")
    print(f"trial spend now {spent()}/{BUDGET}")


asyncio.run(main())
