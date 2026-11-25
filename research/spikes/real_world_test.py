"""Day-0 D3: run our own recordings through Aletheia (REST), clean + WhatsApp-quality copies.

Usage (from the repo root, with DETECTIF_API_KEY in .env):
  .venv/Scripts/python research/spikes/real_world_test.py            # convert + show credits only
  .venv/Scripts/python research/spikes/real_world_test.py --run      # also run the checks (costs credits)

Recordings live in research/real-audio/ (gitignored). Raw results go to research/real-audio/results/.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import httpx
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import config  # noqa: E402  (loads .env; the key is never printed)

AUDIO = ROOT / "research" / "real-audio"
WA = AUDIO / "whatsapp"
OUT = AUDIO / "results"

# standard name -> the file name the phone gave it (truth is "real" unless the name starts with clone/spliced)
FILES = {
    "real_en": "Script A - English.m4a",
    "real_hi": "Script 1 - Hindi.m4a",
    "real_kn": "Script 1 - Kannada.m4a",
    "notice_en": "Script B - English.m4a",
    "notice_hi": "Script B - Hindi.m4a",
    "notice_kn": "Script 2 - Kannada.m4a",
    "clone_en": "clone_en.mp3",
    "spliced_en": "spliced_en.wav",
}


def to_whatsapp(src: Path, dst: Path) -> None:
    """Opus in OGG, mono 16 kHz, 16 kb/s: what WhatsApp does to a voice note (approximately)."""
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(src),
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "16k", str(dst)],
                   check=True)


def headers(extra: dict | None = None) -> dict:
    return {"Authorization": f"Bearer {config.DETECTIF_API_KEY}", **(extra or {})}


def credits(client: httpx.Client) -> None:
    r = client.get(f"{config.DETECTIF_BASE_URL}/v1/credits", headers=headers())
    print("credits:", r.status_code, r.text[:300])


def detect(client: httpx.Client, path: Path) -> dict:
    data = path.read_bytes()
    r = client.post(f"{config.DETECTIF_BASE_URL}/v1/deepfake/detect",
                    headers=headers({"Idempotency-Key": hashlib.sha256(data).hexdigest()}),
                    files={"file": (path.name, data)})
    return {"status": r.status_code, **r.json()}


def summary(name: str, resp: dict) -> str:
    res = resp.get("result") or {}
    if resp["status"] != 200:
        return f"| {name} | error {resp['status']} {resp.get('error', {}).get('code', '')} | | | |"
    segs = res.get("segments", [])
    fake = [f"{s['start']:g}-{s['end']:g}" for s in segs if s.get("verdict") == "fake"]
    top = max((s["score"] for s in segs), default=0)
    verdict = res.get("verdict") or res.get("label")
    return (f"| {name} | {verdict} ({res.get('score', 0):.3f}) | {top:.3f} | "
            f"{len(fake)}/{len(segs)} | {', '.join(fake) or '-'} |")


def main() -> None:
    if not config.DETECTIF_API_KEY:
        sys.exit("DETECTIF_API_KEY is empty in .env")
    WA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    clips = []
    for name, fname in FILES.items():
        src = AUDIO / fname
        if not src.exists():
            print("missing (skipped):", fname)
            continue
        wa = WA / f"{name}.ogg"
        to_whatsapp(src, wa)
        clips += [(f"{name} (clean)", src), (f"{name} (whatsapp)", wa)]
    print(f"{len(clips)} clips ready")

    with httpx.Client(timeout=120) as client:
        credits(client)
        if "--run" not in sys.argv:
            return
        rows = []
        for label, path in clips:
            resp = detect(client, path)
            (OUT / f"{label.replace(' (', '_').rstrip(')')}.json").write_text(
                json.dumps(resp, indent=1, ensure_ascii=False), encoding="utf-8")
            rows.append(summary(label, resp))
            print(rows[-1])
        credits(client)
    print("\n| Clip | Overall | Top segment | Fake windows | Where |\n|---|---|---|---|---|")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
