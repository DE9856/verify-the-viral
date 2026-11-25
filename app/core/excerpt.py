"""Lane A — cut the AI-sounding part out of a checked clip, so people can *hear* it in the chat.

    part = await fake_part(result)      # None unless band == "partly_fake" and the audio is stored
    if part:
        path, (start, end) = part       # OGG/Opus voice note of exactly that stretch

Takes the longest core region (PLAN.md §3: seconds covered by >= 2 overlapping fake windows), with
exact bounds so the clip matches the seconds we name, and 50 ms fades so it doesn't click.
Telegram shows OGG/Opus as a playable voice note. Files are cached in data/audio/excerpts/.
"""
import asyncio
import os
import tempfile
from pathlib import Path

from app import config
from app.core import normalize, store

MAX_SECONDS = 30.0     # a long region is still one listenable voice note
FADE = 0.05


def excerpt_dir() -> Path:
    d = config.DB_PATH.parent / "audio" / "excerpts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pick_region(core_regions: list) -> list[float] | None:
    """Longest region; the earliest one wins a tie."""
    if not core_regions:
        return None
    return list(max(core_regions, key=lambda r: (r[1] - r[0], -r[0])))


def cut_sync(src: str, start: float, end: float) -> str:
    end = min(end, start + MAX_SECONDS)
    dur = round(end - start, 3)
    if dur <= 0:
        raise ValueError("empty region")
    stem = Path(src).stem[:24]
    final = excerpt_dir() / f"{stem}_{start:g}-{end:g}.ogg"
    if final.exists():
        return str(final)
    fades = f"afade=t=in:d={FADE},afade=t=out:st={max(dur - FADE, 0):g}:d={FADE}"
    with tempfile.TemporaryDirectory(dir=excerpt_dir(), ignore_cleanup_errors=True) as tmp:
        out = os.path.join(tmp, "part.ogg")
        normalize._ffmpeg(["-ss", f"{start:g}", "-i", src, "-t", f"{dur:g}", "-vn", "-map", "0:a:0",
                           "-af", fades, "-ac", "1", "-ar", "48000", "-c:a", "libopus", "-b:a", "48k", out])
        normalize._place(out, final)          # never overwrites (Windows-safe, see normalize.py)
    return str(final)


async def fake_part(result: dict) -> tuple[str, list[float]] | None:
    """(path to an OGG/Opus clip, [start, end]) for a partly-fake result, else None."""
    if result.get("band") != "partly_fake":
        return None
    region = pick_region(result.get("core_regions") or [])
    src = store.audio_path(result["id"]) if result.get("id") else None
    if not region or not src or not os.path.exists(src):
        return None
    region[1] = min(region[1], region[0] + MAX_SECONDS)
    path = await asyncio.to_thread(cut_sync, src, region[0], region[1])
    return path, region
