"""Real-API end-to-end check of edits.py: the original + 4 edited copies through check() on a fresh DB.

    DB_PATH=data/edit-e2e.db MOCK_ALETHEIA= PYTHONPATH=. python research/spikes/edit_copy_e2e.py
Costs are appended to research/results/credit_trials.jsonl (counts toward the trial budget).
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from credit_trials import BUDGET, LEDGER, spent  # noqa: E402

from app import config  # noqa: E402
from app.core import check  # noqa: E402

EDIT = Path.home() / "Downloads/edit-test"
FILES = [Path("research/test-audio/spliced_whatsapp.mp3")] + sorted(EDIT.glob("[1-4]_*.mp3"))
FULL = {"1_replace_3s_at_2s": 50, "2_insert_2s_at_18s": 54, "3_cut_3s_at_16s": 44, "4_replace_1s_at_20s": 50}


async def main():
    assert not config.MOCK_ALETHEIA and "e2e" in str(config.DB_PATH), "set DB_PATH=data/edit-e2e.db and MOCK_ALETHEIA="
    if spent() + 41 + 4 * 21 > BUDGET:
        sys.exit("REFUSED: trial budget")
    for f in FILES:
        r = await check.check(str(f), source={"channel": "web", "filename": f.name})
        e = r.get("edited_copy_of") or {}
        row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "trial": f"E2E_{f.stem}", "idea": "edited-part-only e2e",
               "file": f.name, "charged": r["credits_charged"], "band": r["band"], "core_regions": r["core_regions"],
               "mode": e.get("mode"), "rechecked": e.get("rechecked"), "changed": e.get("changed"),
               "removed": e.get("removed"), "full_check_on_server": FULL.get(f.stem)}
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        print(json.dumps(row))
    print(f"trial spend now {spent()}/{BUDGET}")


asyncio.run(main())
