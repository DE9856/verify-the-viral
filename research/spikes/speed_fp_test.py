"""Speed-tolerant fingerprint matching: can a sped-up / slowed-down copy match its stored original?

Run from the repo root (uses app.core.fingerprint.similarity and bin/fpcalc):
    PYTHONPATH=. .venv/Scripts/python research/spikes/speed_fp_test.py

No API calls, 0 credits. Three methods, each giving a score per (query, stored clip):
  A  fp-stretch   resample the stored fingerprint to the query's timeline (numpy only)
  B  audio-fix    undo the speed with ffmpeg (atempo, or asetrate for pitch-shifted copies),
                  re-run fpcalc, compare
  C  fusion       sweep many speed ratios with A (cheap, no reliance on duration), take the best
                  2 ratios, confirm them with B; score = best B score
  C2 fusion v2    B at the duration ratio in both modes (tempo, pitch) + B at A's refined peak;
                  what production would run, since it doesn't know the mode or whether it was trimmed
A and B use the speed implied by the two durations; C searches, so it also survives a trim.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from app.core.fingerprint import similarity

ROOT = Path(__file__).resolve().parents[2]
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPCALC = str(ROOT / "bin" / ("fpcalc.exe" if sys.platform == "win32" else "fpcalc"))
AUDIO = ROOT / "research" / "test-audio"
SPEEDS = [0.5, 0.75, 1.25, 1.5, 1.75, 2.0]
GRID = np.round(np.arange(0.48, 2.06, 0.02), 2)   # speeds C sweeps
TMP = Path(tempfile.mkdtemp(prefix="speedfp_"))


def ff(*args):
    subprocess.run([FF, "-v", "error", "-y", *map(str, args)], check=True)


def fp(path) -> tuple[np.ndarray, float]:
    out = json.loads(subprocess.run([FPCALC, "-raw", "-json", "-length", "300", str(path)],
                                    capture_output=True, check=True, text=True).stdout)
    return np.array(out["fingerprint"], dtype=np.uint32), float(out["duration"])


def speed_copy(src, s, mode="tempo", trim=0.0, tag=""):
    out = TMP / f"{Path(src).stem}_{mode}{s}{tag}.mp3"
    filt = f"atempo={s}" if mode == "tempo" else f"aresample=44100,asetrate=44100*{s},aresample=44100"
    ff("-ss", trim, "-i", src, "-filter:a", filt, "-b:a", "64k", out)
    return out


def stretch(f: np.ndarray, s: float, n: int) -> np.ndarray:
    """Stored fingerprint f (original speed) as a copy played at speed s would look: n frames."""
    idx = np.round(np.arange(n) * s).astype(int)
    return f[idx[idx < len(f)]]


def score_a(q, stored, s):
    return similarity(q, stretch(stored, s, len(q)))


def score_b(qpath, s, mode):
    fixed = TMP / f"fix_{Path(qpath).stem}_{mode}{s:.2f}.wav"
    t = 1 / s   # atempo accepts 0.5..100: chain two for slower
    tempo = f"atempo={t:.6f}" if t >= 0.5 else f"atempo=0.5,atempo={2 * t:.6f}"
    filt = tempo if mode == "tempo" else f"aresample=44100,asetrate=44100/{s:.6f},aresample=44100"
    ff("-i", qpath, "-ac", "1", "-filter:a", filt, fixed)
    return fp(fixed)[0]


def main():
    stored = {n: fp(AUDIO / f) for n, f in [("spliced", "spliced_whatsapp.mp3"), ("real_en", "real_en.wav"),
                                            ("fake_en", "fake_en.mp3"), ("fake_hi", "fake_hi.mp3"),
                                            ("fake_kn", "fake_kn.mp3")]}
    queries = []   # (label, path, true source or None, mode)
    for s in SPEEDS:
        queries.append((f"spliced tempo {s}x", speed_copy(AUDIO / "spliced_whatsapp.mp3", s), "spliced", "tempo"))
    for s in SPEEDS:   # tape-style: speed and pitch change together
        queries.append((f"spliced PITCH {s}x", speed_copy(AUDIO / "spliced_whatsapp.mp3", s, "pitch"), "spliced", "pitch"))
    for s in (0.75, 1.5, 2.0):
        queries.append((f"real_en PITCH {s}x", speed_copy(AUDIO / "real_en.wav", s, "pitch"), "real_en", "pitch"))
    queries.append(("spliced PITCH 1.5x +trim 3s", speed_copy(AUDIO / "spliced_whatsapp.mp3", 1.5, "pitch", trim=3, tag="t"),
                    "spliced", "pitch"))
    queries.append(("spliced tempo 1.5x +trim 3s", speed_copy(AUDIO / "spliced_whatsapp.mp3", 1.5, trim=3, tag="t"),
                    "spliced", "tempo"))
    for s in (0.75, 1.25, 1.5, 2.0):   # real_en shares its first 10 s with spliced: the key negative
        queries.append((f"real_en tempo {s}x", speed_copy(AUDIO / "real_en.wav", s), "real_en", "tempo"))
    for s in (1.25, 1.5):
        queries.append((f"fake_en tempo {s}x", speed_copy(AUDIO / "fake_en.mp3", s), "fake_en", "tempo"))

    rows, timing = [], {"A": [], "B": [], "C": [], "C2": []}
    for label, path, truth, mode in queries:
        q, qdur = fp(path)
        for name, (sf, sdur) in stored.items():
            s_len = sdur / qdur                       # speed implied by durations
            plain = similarity(q, sf)
            t = time.perf_counter(); a = score_a(q, sf, s_len); timing["A"].append(time.perf_counter() - t)
            t = time.perf_counter(); b = similarity(score_b(path, s_len, mode), sf) if 0.45 <= s_len <= 2.1 else 0.0
            timing["B"].append(time.perf_counter() - t)
            t = time.perf_counter()
            sweep = sorted(((score_a(q, sf, g), g) for g in GRID), reverse=True)
            top, picked = [], []
            for sc, g in sweep:                       # 2 best ratios that aren't neighbours
                if all(abs(g - p) > 0.05 for p in picked):
                    picked.append(g); top.append((sc, g))
                if len(top) == 2:
                    break
            c, c_s = max((similarity(score_b(path, g, mode), sf), g) for _, g in top)
            timing["C"].append(time.perf_counter() - t)
            # C2: what production would do without knowing the copy's mode or whether it was trimmed:
            # B at the length ratio in BOTH modes, plus B (tempo) at A's peak refined to 0.005 steps
            t = time.perf_counter()
            peak = top[0][1]
            fine = max((score_a(q, sf, g), g) for g in np.round(np.arange(peak - 0.02, peak + 0.021, 0.005), 3))[1]
            cands = [(s_len, "tempo"), (s_len, "pitch"), (float(fine), "tempo")]
            c2, c2_s, c2_m = max((similarity(score_b(path, g, m), sf), round(g, 3), m)
                                 for g, m in cands if 0.45 <= g <= 2.1)
            timing["C2"].append(time.perf_counter() - t)
            rows.append(dict(query=label, stored=name, same=(name == truth), s_len=round(s_len, 3),
                             plain=round(plain, 3), A=round(a, 3), B=round(b, 3), C=round(c, 3), C_speed=c_s, C2=round(c2, 3), C2_speed=c2_s, C2_mode=c2_m,
                             A_peak=top[0][1]))

    print(f"{'query':30} {'stored':8} same  s_len  plain   A      B      C      C2   C2@speed")
    for r in rows:
        if r["same"] or max(r["A"], r["B"], r["C"], r["C2"]) >= 0.65:      # positives + any worrying negative
            print(f"{r['query']:30} {r['stored']:8} {'YES ' if r['same'] else 'no  '} {r['s_len']:5}  "
                  f"{r['plain']:.3f}  {r['A']:.3f}  {r['B']:.3f}  {r['C']:.3f}  {r['C2']:.3f}  {r['C2_speed']} {r['C2_mode']}")
    print("\nBest score of a DIFFERENT clip (must stay < 0.80):")
    for m in ("plain", "A", "B", "C", "C2"):
        worst = max((r for r in rows if not r["same"]), key=lambda r: r[m])
        print(f"  {m:5} {worst[m]:.3f}  ({worst['query']} vs {worst['stored']})")
    print("\nLowest score of the SAME clip, tempo copies only (want >= 0.80):")
    for m in ("plain", "A", "B", "C", "C2"):
        pos = [r for r in rows if r["same"] and "PITCH" not in r["query"]]
        low = min(pos, key=lambda r: r[m])
        print(f"  {m:5} {low[m]:.3f}  ({low['query']})")
    print("\nLowest score of the SAME clip, pitch-shifted copies (want >= 0.80):")
    for m in ("A", "B", "C", "C2"):
        low = min((r for r in rows if r["same"] and "PITCH" in r["query"]), key=lambda r: r[m])
        print(f"  {m:5} {low[m]:.3f}  ({low['query']})")
    print("\nms per comparison: " + ", ".join(f"{k} {1000 * np.mean(v):.1f}" for k, v in timing.items()))
    (ROOT / "research" / "results" / "speed_fp_test.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
