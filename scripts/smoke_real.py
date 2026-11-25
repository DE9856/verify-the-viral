"""Lane A "done when" against the REAL Aletheia API (needs DETECTIF_API_KEY in .env).
Run: python -m scripts.smoke_real          (≈ 200 credits: five clips, ~96 s of audio)

Checks each recorded test clip through the full pipeline and compares the band with what we
expect, then re-sends the WhatsApp copy of the spliced clip to prove the fingerprint cache
answers for 0 credits. Uses its own database (data/smoke.db), so your real data stays clean.
"""
import asyncio
import json
import time
from pathlib import Path

from app import config
from app.core import aletheia, check as check_mod

AUDIO = config.ROOT / "research" / "test-audio"
EXPECTED = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))
CLIPS = ["real_en.wav", "fake_en.mp3", "fake_hi.mp3", "fake_kn.mp3", "spliced_en.wav", "spliced_whatsapp.ogg"]


async def main() -> int:
    if not config.DETECTIF_API_KEY:
        print("Set DETECTIF_API_KEY in .env first (copy env.example to .env).")
        return 2
    config.MOCK_ALETHEIA = ""
    config.DB_PATH = config.ROOT / "data" / "smoke.db"
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    before = (await aletheia.credits()).get("available")
    print(f"credits before: {before}\n")
    print(f"{'clip':22} {'band':12} {'expected':12} {'core':16} {'credits':>7} {'cache':>6} {'ms':>6}")
    failures = 0
    for name in CLIPS:
        t0 = time.perf_counter()
        r = await check_mod.check(str(AUDIO / name), source={"channel": "smoke", "tg_file_unique_id": None,
                                                             "filename": name})
        ms = 1000 * (time.perf_counter() - t0)
        exp = EXPECTED[Path(name).stem]["band"]
        ok = r["band"] == exp
        failures += not ok
        print(f"{name:22} {r['band']:12} {exp:12} {str(r['core_regions']):16} {r['credits_charged']:>7} "
              f"{str(r['cache']['hit']):>6} {ms:6.0f} {'✓' if ok else '✗ ' + str(r.get('error'))}")
    after = (await aletheia.credits()).get("available")
    print(f"\ncredits after: {after}  (used {before - after if before is not None and after is not None else '?'})")
    print("spliced_whatsapp should be a cache hit (fingerprint) with 0 credits." )
    print("ALL GOOD" if not failures else f"{failures} clip(s) differ from the recorded results — look before the demo")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
