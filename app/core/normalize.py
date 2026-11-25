"""Lane A · step A1 — turn any upload (voice note, audio file, video) into one clean audio file.

Tested recipe (research/spikes/spike_server.py, 0.3–0.5 s per file):
    ffmpeg -v error -y -i <src> -vn -ac 1 -ar 16000 -t 300 -c:a libopus -b:a 32k out.ogg
ffmpeg comes from imageio_ffmpeg.get_ffmpeg_exe() (no system install needed).
Run ffmpeg in a thread (asyncio.to_thread) so the bot/API loop isn't blocked.
"""
from dataclasses import dataclass


@dataclass
class Normalized:
    path: str        # mono 16 kHz Opus .ogg
    sha256: str      # of the normalised bytes → Aletheia Idempotency-Key
    duration: float  # seconds
    trimmed: bool    # True if the input was longer than 300 s


async def normalize(src_path: str) -> Normalized:
    raise NotImplementedError("Lane A · A1: normalize()")
