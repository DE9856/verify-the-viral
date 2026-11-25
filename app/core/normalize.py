"""Lane A · step A1 — turn any upload (voice note, audio file, video) into a file Aletheia accepts,
doing as little work as possible.

Three paths, cheapest first:
  passthrough  audio-only file Aletheia already accepts, <= 300 s, <= 20 MB  → send the original bytes
               (no generation loss; a Telegram voice note never gets re-encoded)
  copy         video, or audio > 300 s, whose audio codec Aletheia accepts → `-c:a copy` (no re-encode)
  transcode    anything else → mono 16 kHz Opus 48 kbps

Output goes to data/audio/<sha256>.<ext>: kept so the result page can draw the waveform, and named
by content so the same clip is only stored once.
"""
import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg

from app import config

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
PASSTHROUGH_MAX_BYTES = 20 * 1024 * 1024   # bigger files get compressed (API needs >= 64 KB/s upload)
API_MAX_BYTES = 100 * 1024 * 1024

# audio codec → (container extension for a stream copy, Aletheia accepts it)
COPYABLE = {"opus": ".ogg", "vorbis": ".ogg", "aac": ".m4a", "mp3": ".mp3", "flac": ".flac"}
# ffmpeg demuxer name → audio codecs we can send unchanged when the file has no video
PASSTHROUGH = {
    "ogg": {"opus", "vorbis", "flac"},
    "mp3": {"mp3"},
    "flac": {"flac"},
    "wav": {"pcm_s16le", "pcm_s24le", "pcm_f32le", "pcm_u8", "pcm_mulaw", "pcm_alaw"},
    "aiff": {"pcm_s16be", "pcm_s24be"},
    "mov,mp4,m4a,3gp,3g2,mj2": {"aac"},
    "matroska,webm": {"opus", "vorbis"},
}
EXT_FOR_DEMUXER = {"ogg": ".ogg", "mp3": ".mp3", "flac": ".flac", "wav": ".wav", "aiff": ".aiff",
                   "mov,mp4,m4a,3gp,3g2,mj2": ".m4a", "matroska,webm": ".webm"}


class NormalizeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code            # no_audio | unreadable | too_large


@dataclass
class Probe:
    demuxer: str
    duration: float
    audio_codec: str | None
    has_video: bool


@dataclass
class Normalized:
    path: str        # file to send to Aletheia (and to play on the result page)
    sha256: str      # of that file's bytes → Idempotency-Key + exact cache key
    duration: float  # seconds actually sent
    trimmed: bool    # True if the input was longer than 300 s
    method: str      # passthrough | copy | transcode


def audio_dir() -> Path:
    d = config.DB_PATH.parent / "audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def probe(src: str) -> Probe:
    """Read container, duration and codecs from ffmpeg's banner (no ffprobe in imageio-ffmpeg)."""
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", src], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    m = re.search(r"Input #0, ([^,]+(?:,[a-z0-9]+)*), from", out)
    if not m:
        raise NormalizeError("unreadable", "Not an audio or video file ffmpeg can read")
    dur = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", out)
    duration = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else 0.0
    a = re.search(r"Stream #\S+.*?: Audio: ([a-z0-9_]+)", out)
    return Probe(demuxer=m[1], duration=duration, audio_codec=a[1] if a else None,
                 has_video=bool(re.search(r"Stream #\S+.*?: Video: (?!mjpeg|png)", out)))  # cover art isn't video


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ffmpeg(args: list[str]) -> None:
    r = subprocess.run([FFMPEG, "-v", "error", "-y", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise NormalizeError("unreadable", f"ffmpeg failed: {r.stderr.strip()[:200]}")


def normalize_sync(src: str) -> Normalized:
    size = os.path.getsize(src)
    if size > API_MAX_BYTES * 5:  # we'd still trim, but refuse absurd uploads early
        raise NormalizeError("too_large", "File is too large")
    p = probe(src)
    if not p.audio_codec:
        raise NormalizeError("no_audio", "The file has no audio track")
    trimmed = p.duration > config.MAX_SECONDS
    send_seconds = min(p.duration, config.MAX_SECONDS) if p.duration else 0.0

    # ignore_cleanup_errors: on Windows, antivirus can briefly lock a fresh file; a leftover temp
    # folder is harmless, a failed check is not.
    with tempfile.TemporaryDirectory(dir=audio_dir(), ignore_cleanup_errors=True) as tmp:
        if (not p.has_video and not trimmed and size <= PASSTHROUGH_MAX_BYTES
                and p.audio_codec in PASSTHROUGH.get(p.demuxer, ())):
            method, ext = "passthrough", EXT_FOR_DEMUXER[p.demuxer]
            out = os.path.join(tmp, "out" + ext)
            shutil.copyfile(src, out)
        elif p.audio_codec in COPYABLE:
            method, ext = "copy", COPYABLE[p.audio_codec]
            out = os.path.join(tmp, "out" + ext)
            _ffmpeg(["-i", src, "-vn", "-map", "0:a:0", "-t", str(config.MAX_SECONDS), "-c:a", "copy", out])
        else:
            method, ext = "transcode", ".ogg"
            out = os.path.join(tmp, "out.ogg")
            _ffmpeg(["-i", src, "-vn", "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                     "-t", str(config.MAX_SECONDS), "-c:a", "libopus", "-b:a", "48k", out])
        if os.path.getsize(out) > API_MAX_BYTES:
            raise NormalizeError("too_large", "Audio is still larger than 100 MB after compressing")
        digest = _sha256(out)
        final = audio_dir() / f"{digest}{ext}"
        _place(out, final)
    return Normalized(path=str(final), sha256=digest, duration=round(send_seconds, 3),
                      trimmed=trimmed, method=method)


def _rename_no_clobber(src: str | Path, final: Path) -> None:
    """Never overwrite an existing file: on Windows, replacing a file another request is about to
    open puts it in a 'delete pending' state and that open fails (PermissionError). The name is the
    content hash, so an existing file already has the right bytes."""
    if os.name == "nt":
        try:
            os.rename(src, final)          # fails if final exists — which is fine
        except FileExistsError:
            pass
    elif not final.exists():
        os.rename(src, final)              # POSIX rename is atomic; open readers keep the old file


def _place(out: str, final: Path) -> None:
    """Move `out` to its content-addressed name. Retry briefly if antivirus locks the fresh file,
    then fall back to a copy (a copy only needs read access)."""
    for attempt in range(6):
        if final.exists():                 # same clip normalised before (or concurrently)
            return
        try:
            _rename_no_clobber(out, final)
            return
        except OSError:
            time.sleep(0.05 * (attempt + 1))
    if not final.exists():
        part = final.with_name(final.name + f".{os.getpid()}.part")
        shutil.copyfile(out, part)
        try:
            _rename_no_clobber(part, final)
        except OSError:
            if not final.exists():
                raise


async def normalize(src_path: str) -> Normalized:
    return await asyncio.to_thread(normalize_sync, src_path)
