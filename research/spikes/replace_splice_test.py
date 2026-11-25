"""Replacement splice: swap N seconds of a real clip for the same number of seconds of its clone,
so the length and the alignment of everything else stay the same. Plain fingerprint score vs the real."""
import subprocess, sys
from pathlib import Path
import imageio_ffmpeg
from app.core import fingerprint
FF = imageio_ffmpeg.get_ffmpeg_exe(); WA = Path("research/real-audio/whatsapp"); OUT = Path(sys.argv[1])
def dur(p): return float(subprocess.run([str(fingerprint.fpcalc_path()), "-json", str(p)], capture_output=True, text=True).stdout.split('"duration":')[1].split(",")[0])
for lang in ("en", "hi", "kn"):
    real, clone = WA / f"notice_{lang}.ogg", WA / f"clone_{lang}.ogg"
    d = dur(real); fr = fingerprint.compute(str(real))
    for secs in (2, 3, 5, 8):
        if secs > d * 0.6: continue
        a = d * 0.4; out = OUT / f"replace_{lang}_{secs}.wav"
        subprocess.run([FF, "-v", "error", "-y", "-i", str(real), "-i", str(clone), "-filter_complex",
            f"[0:a]aresample=16000,atrim=0:{a},asetpts=N/SR/TB[x];[1:a]aresample=16000,atrim=1:{1+secs},asetpts=N/SR/TB[y];"
            f"[0:a]aresample=16000,atrim={a+secs},asetpts=N/SR/TB[z];[x][y][z]concat=n=3:v=0:a=1,aformat=channel_layouts=mono[o]",
            "-map", "[o]", str(out)], check=True)
        print(f"notice_{lang} ({d:.0f} s), {secs} s replaced ({100*secs/d:.0f}%): plain score {fingerprint.similarity(fingerprint.compute(str(out)), fr):.3f}")
