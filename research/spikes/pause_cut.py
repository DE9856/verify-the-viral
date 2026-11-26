"""Cut pauses out of a clip and keep a map back to the original timeline (credit trials, idea B).

A pause = a run of 20 ms frames more than DROP dB below the clip's own loud level (95th percentile),
so it adapts to room noise. Each pause of >= min_pause s is shortened to `keep` s (half kept on each
side), with 10 ms fades at the joins. Returns the cut audio and `pieces`: [new_start, orig_start, length]
for every kept stretch, so a time t in the cut clip maps back to orig_start + (t - new_start).
"""
import subprocess

import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 16000
FRAME = 320            # 20 ms
DROP = 25.0            # dB below the loud level = pause


def decode(path: str) -> np.ndarray:
    b = subprocess.run([FF, "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(b, np.int16).astype(np.float32) / 32768


def pauses(x: np.ndarray, min_pause: float) -> list[tuple[int, int]]:
    """[start, end) sample ranges of pauses >= min_pause seconds."""
    n = len(x) // FRAME
    e = 20 * np.log10(np.sqrt((x[:n * FRAME].reshape(n, FRAME) ** 2).mean(1)) + 1e-9)
    quiet = e < np.percentile(e, 95) - DROP
    edges = np.flatnonzero(np.diff(np.concatenate([[0], quiet.astype(np.int8), [0]])))
    out = []
    for a, b in zip(edges[::2], edges[1::2]):
        if (b - a) * FRAME >= min_pause * SR:
            out.append((a * FRAME, b * FRAME))
    return out


def cut(x: np.ndarray, min_pause: float, keep: float, lead_trail: bool = True):
    """Returns (cut audio, pieces, seconds removed). lead_trail: also trim silence at both ends to keep/2."""
    half = int(keep * SR / 2)
    fade = int(0.01 * SR)
    drops = []
    for a, b in pauses(x, min_pause):
        at_start, at_end = a == 0, b >= len(x) - FRAME
        if (at_start or at_end) and not lead_trail:
            continue
        lo = a if at_start else a + half
        hi = b if at_end else b - half
        if at_start:
            hi = b - half
        if at_end:
            lo = a + half
        if hi > lo:
            drops.append((lo, hi))
    pieces, parts, pos, new = [], [], 0, 0
    for lo, hi in drops + [(len(x), len(x))]:
        if lo > pos:
            seg = x[pos:lo].copy()
            if len(seg) > 2 * fade:
                seg[:fade] *= np.linspace(0, 1, fade) if pos > 0 else 1
                seg[-fade:] *= np.linspace(1, 0, fade) if lo < len(x) else 1
            parts.append(seg)
            pieces.append([round(new / SR, 3), round(pos / SR, 3), round(len(seg) / SR, 3)])
            new += len(seg)
        pos = hi
    y = np.concatenate(parts) if parts else x
    return y, pieces, round((len(x) - len(y)) / SR, 2)


def to_original(t: float, pieces: list) -> float:
    """A time in the cut clip → the same moment in the original."""
    for new_start, orig_start, length in reversed(pieces):
        if t >= new_start - 1e-9:
            return round(orig_start + min(t - new_start, length), 2)
    return t


def write_wav(path: str, y: np.ndarray):
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run([FF, "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", path],
                   input=pcm, check=True)
