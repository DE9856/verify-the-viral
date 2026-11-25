"""Compare dedup/fingerprint approaches for 'already checked' cache (idea 7)."""
import hashlib, json, subprocess, sys, time
import numpy as np
from scipy.signal import stft
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
import os
FPCALC = os.path.abspath("dl/fpcalc/chromaprint-fpcalc-1.5.1-windows-x86_64/fpcalc.exe")
REF = "audio/spliced_en.wav"
SAME = {  # should MATCH the reference
    "opus16k (WhatsApp)": "audio/spliced_whatsapp.ogg",
    "opus re-forward x2": "audio/v_reforward.ogg",
    "mp3 64k": "audio/v_mp3.mp3",
    "aac from mp4 video": "audio/v_fromvideo.m4a",
    "trimmed 1.3s start": "audio/v_trim.wav",
    "volume -6dB": "audio/v_quiet.wav",
}
DIFF = {  # should NOT match
    "real_en (same first 10s!)": "audio/real_en.wav",
    "other human clip": "audio/OSR_us_000_0011_8k.wav",
    "fake_en TTS": "audio/fake_en.mp3",
}


def pcm(path, sr=8000):
    raw = subprocess.run([FF, "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


# --- A/B: exact hashes -----------------------------------------------------
def sha_file(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def sha_pcm(p): return hashlib.sha256(pcm(p).tobytes()).hexdigest()


# --- C: chromaprint ---------------------------------------------------------
def chroma(p):
    out = subprocess.run([FPCALC, "-raw", "-json", "-length", "300", p], capture_output=True, check=True).stdout
    return np.array(json.loads(out)["fingerprint"], dtype=np.uint32)


def ber_sim(a, b, max_off=60, min_overlap=20):
    """best (1 - bit error rate) over offsets; works for uint32 (chromaprint) or packed bool rows."""
    best = 0.0
    for off in range(-max_off, max_off + 1):
        x, y = (a[off:], b) if off >= 0 else (a, b[-off:])
        n = min(len(x), len(y))
        if n < min_overlap:
            continue
        x, y = x[:n], y[:n]
        if x.dtype == np.uint32:
            diff = np.unpackbits((x ^ y).view(np.uint8)).sum()
            bits = n * 32
        else:
            diff = (x != y).sum(); bits = x.size
        # penalise partial overlap: similarity over the LONGER clip's length
        cover = n / max(len(a), len(b))
        best = max(best, (1 - diff / bits) * cover + 0.5 * (1 - cover))
    return best


# --- D: home-made Philips-style fingerprint (numpy only) -------------------
def philips(p):
    x = pcm(p, 5000)
    f, t, Z = stft(x, fs=5000, nperseg=2048, noverlap=2048 - 64)
    edges = np.geomspace(300, 2000, 34)
    E = np.stack([np.abs(Z[(f >= lo) & (f < hi)]).sum(0) ** 2 for lo, hi in zip(edges[:-1], edges[1:])])
    dE = E[:-1] - E[1:]                      # band differences (32 x T)
    bits = (dE[:, 1:] - dE[:, :-1]) > 0      # time differences
    return bits.T                            # T x 32 bool


def run():
    rows = []
    ref = {"sha_file": sha_file(REF), "sha_pcm": sha_pcm(REF)}
    t0 = time.time(); ref["chroma"] = chroma(REF); tc = time.time() - t0
    t0 = time.time(); ref["philips"] = philips(REF); tp = time.time() - t0
    for group, items in (("SAME", SAME), ("DIFF", DIFF)):
        for name, path in items.items():
            rows.append((group, name,
                         sha_file(path) == ref["sha_file"],
                         sha_pcm(path) == ref["sha_pcm"],
                         ber_sim(ref["chroma"], chroma(path)),
                         ber_sim(ref["philips"], philips(path), max_off=150, min_overlap=200)))
    print(f"{'':5} {'variant':28} {'sha(file)':>9} {'sha(pcm)':>8} {'chroma':>7} {'philips':>7}")
    for g, n, a, b, c, d in rows:
        print(f"{g:5} {n:28} {str(a):>9} {str(b):>8} {c:7.3f} {d:7.3f}")
    print(f"fingerprint time on 25s clip: chromaprint {tc*1000:.0f} ms, philips {tp*1000:.0f} ms")


run()
