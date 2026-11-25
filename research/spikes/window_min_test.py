"""Worst ~2 s window at the best alignment: same clip (re-encodes, layer-5 undo) vs replacement splices."""
import subprocess, sys
from pathlib import Path
import numpy as np, imageio_ffmpeg
from app.core import fingerprint, variants
FF = imageio_ffmpeg.get_ffmpeg_exe(); S = Path(sys.argv[1]); WA = Path("research/real-audio/whatsapp"); TA = Path("research/test-audio")
DEMO = Path.home() / "Downloads/demo-clips"; ST = Path.home() / "Downloads/speed-test-2"
W = 16  # frames ≈ 2 s
def windows(a, b):
    x, y = np.asarray(a, np.uint32), np.asarray(b, np.uint32); best = None
    for off in range(-60, 61):
        u, v = (x[off:], y) if off >= 0 else (x, y[-off:]); n = min(len(u), len(v))
        if n < 20: continue
        bits = np.unpackbits((u[:n] ^ v[:n]).view(np.uint8)).reshape(n, 32).sum(1)
        m = 1 - bits.sum() / (n * 32)
        if best is None or m > best[0]: best = (m, bits)
    per = 1 - best[1] / 32
    win = np.convolve(per, np.ones(W) / W, "valid")
    return fingerprint.similarity(a, b), win.min()
def fp(p): return fingerprint.compute(str(p))
def undo(p, kind, v):
    out = S / f"undo_{Path(p).stem}.wav"
    subprocess.run([FF, "-v", "error", "-y", "-i", str(p), "-ac", "1", "-filter:a", variants._filter(kind, v), str(out)], check=True); return fp(out)
rows = []
for a, b in [("notice_en", "demo/AUD-20261125-WA0012"), ("spliced_en", "demo/AUD-20261125-WA0011"), ("clone_en", "demo/AUD-20261125-WA0013")]:
    pb = DEMO / (b.split("/")[1] + ".ogg"); rows.append(("SAME real WhatsApp " + a, *windows(fp(WA / f"{a}.ogg"), fp(pb))))
ref = fp(TA / "spliced_en.wav")
for f in ("spliced_whatsapp.ogg", "spliced_whatsapp.mp3", "spliced_whatsapp.m4a"):
    rows.append(("SAME re-encode " + f, *windows(ref, fp(TA / f))))
orig = fp(TA / "spliced_whatsapp.mp3")
for f, kind, v in [("speed_1.8x.mp3", "speed", 1.8), ("speed_1.4x.mp3", "speed", 1.4), ("speed_0.6x.mp3", "speed", 0.6),
                   ("tape_1.3x.mp3", "tape", 1.3), ("pitch_2semitones.mp3", "pitch", -2), ("pitch_-3semitones.mp3", "pitch", 3)]:
    rows.append(("SAME layer5 undo " + f, *windows(undo(ST / f, kind, v), orig)))
for p in sorted(S.glob("replace_*.wav")):
    lang = p.stem.split("_")[1]; rows.append(("SPLICE " + p.stem, *windows(fp(WA / f"notice_{lang}.ogg"), fp(p))))
rows.append(("SPLICE insert notice_en vs spliced_en", *windows(fp(WA / "notice_en.ogg"), fp(WA / "spliced_en.ogg"))))
for name, avg, wmin in rows: print(f"{name:45} average {avg:.3f}   worst 2 s window {wmin:.3f}")
