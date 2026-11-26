"""Real-API check of edge-silence trimming (normalize.trim_plan): padded clips through check().

    DB_PATH=data/edge-e2e.db MOCK_ALETHEIA= PYTHONPATH=. python research/spikes/edge_trim_e2e.py
Baselines (unpadded, research/real-audio/results): spliced_en partly_fake 10-14 s; notice_hi real, 0 fake windows.
"""
import asyncio
import json
import math
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from credit_trials import BUDGET, FF, LEDGER, OUT, spent  # noqa: E402

from app import config  # noqa: E402
from app.core import check  # noqa: E402

PAD = 2.0


def pad(name: str) -> Path:
    dst = OUT / f"E_{name}_pad2s_room.ogg"
    OUT.mkdir(parents=True, exist_ok=True)
    g = (f"[0:a]aformat=sample_rates=16000:channel_layouts=mono[a];"
         f"anoisesrc=r=16000:a=0.0045:c=pink:d={PAD}[n1];anoisesrc=r=16000:a=0.0045:c=pink:d={PAD}[n2];"
         f"[n1][a][n2]concat=n=3:v=0:a=1[o]")
    subprocess.run([FF, "-v", "error", "-y", "-i", f"research/real-audio/whatsapp/{name}.ogg", "-filter_complex", g,
                    "-map", "[o]", "-c:a", "libopus", "-b:a", "16k", str(dst)], check=True, stdin=subprocess.DEVNULL)
    return dst


async def main():
    assert not config.MOCK_ALETHEIA and "e2e" in str(config.DB_PATH)
    if spent() + 120 > BUDGET:
        sys.exit("REFUSED: trial budget")
    for name in sys.argv[1:] or ("spliced_en", "notice_hi"):
        f = pad(name)
        r = await check.check(str(f), source={"channel": "web", "filename": f.name})
        row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "trial": f"EDGE_{name}_grid", "idea": "edge-silence trim e2e",
               "file": f.name, "file_seconds": r["duration"], "charged": r["credits_charged"],
               "untrimmed_price": max(20, math.ceil(2 * r["duration"])), "band": r["band"],
               "core_regions": r["core_regions"], "overall": r["overall"],
               "fake_windows": [[s["start"], s["end"], round(s["score"], 3)] for s in r["segments"] if s.get("verdict") == "fake"]}
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        print(json.dumps(row))
    print(f"trial spend now {spent()}/{BUDGET}")


asyncio.run(main())
