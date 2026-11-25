"""Pure pitch shift (same length, voice higher/deeper): does the cache still recognise the clip?

Run from the repo root:  PYTHONPATH=. .venv/Scripts/python research/spikes/pitch_fp_test.py
No API calls, 0 credits. Shift = asetrate (pitch+speed) then atempo back (speed only), so the
length stays the same. For each shifted copy: plain Chromaprint score, then the best score after
trying to undo shifts of -6..+6 semitones (what a pitch-tolerant cache would have to do).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from app.core.fingerprint import similarity

ROOT = Path(__file__).resolve().parents[2]
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPCALC = str(ROOT / "bin" / ("fpcalc.exe" if sys.platform == "win32" else "fpcalc"))
AUDIO = ROOT / "research" / "test-audio"
TMP = Path(tempfile.mkdtemp(prefix="pitchfp_"))


def fp(path):
    out = subprocess.run([FPCALC, "-raw", "-json", "-length", "300", str(path)], capture_output=True, text=True, check=True)
    return np.array(json.loads(out.stdout)["fingerprint"], dtype=np.uint32)


def shift(src, semis, out):
    r = 2 ** (semis / 12)
    t = 1 / r
    tempo = f"atempo={t:.6f}" if 0.5 <= t <= 100 else f"atempo=0.5,atempo={2 * t:.6f}"
    subprocess.run([FF, "-v", "error", "-y", "-i", str(src), "-filter:a",
                    f"aresample=44100,asetrate=44100*{r:.6f},aresample=44100,{tempo}", str(out)], check=True)
    return out


def main():
    stored = {n: fp(AUDIO / f) for n, f in [("spliced", "spliced_whatsapp.mp3"), ("real_en", "real_en.wav"),
                                            ("fake_en", "fake_en.mp3"), ("fake_hi", "fake_hi.mp3"), ("fake_kn", "fake_kn.mp3")]}
    src = {"spliced": AUDIO / "spliced_whatsapp.mp3", "real_en": AUDIO / "real_en.wav"}
    undo = [float(s) for s in np.arange(-6, 6.01, 0.5) if s]   # half-semitone steps (whole steps left 0.5-off shifts at ~0.77)
    worst_neg = (0, "")
    print(f"{'copy':22} plain-vs-own  best-undo-vs-own (at)   best-vs-other-clip")
    for name, path in src.items():
        for semis in (-4, -2.5, -2, -1, -0.5, 0.5, 1, 1.5, 2, 3.3, 4):   # non-whole shifts: undo grid is whole semitones
            q = shift(path, semis, TMP / f"{name}_{semis}.wav")
            plain = similarity(fp(q), stored[name])
            fixes = {u: fp(shift(q, u, TMP / f"{name}_{semis}_fix{u}.wav")) for u in undo}
            best, at = max((similarity(f, stored[name]), u) for u, f in fixes.items())
            other = max((similarity(f, sf), o) for o, sf in stored.items() if o != name for f in [fp(q), *fixes.values()])
            worst_neg = max(worst_neg, (other[0], f"{name}{semis:+g} vs {other[1]}"))
            print(f"{name} {semis:+g} semitones".ljust(22) + f" {plain:.3f}         {best:.3f} ({at:+g})"
                  f"              {other[0]:.3f} ({other[1]})")
    print(f"\nworst different-clip score over all undo attempts: {worst_neg[0]:.3f} ({worst_neg[1]})")


if __name__ == "__main__":
    main()
