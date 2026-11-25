"""Tune / check app/core/fpdiff.py: true copies must come out "same", edits "edited" at the right seconds.

Run from the repo root:  PYTHONPATH=. .venv/Scripts/python research/spikes/fp_diff_test.py
0 credits. Audio: research/real-audio/whatsapp (consented own voices), research/test-audio,
~/Downloads/demo-clips (real WhatsApp copies), ~/Downloads/speed-test{,-2} (speed/pitch copies).
Every edit is re-encoded to WhatsApp-like Opus 24k before comparing, like a forwarded edit would be.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg

from app.core import fingerprint, fpdiff, variants

ROOT = Path(__file__).resolve().parents[2]
FF = imageio_ffmpeg.get_ffmpeg_exe()
WA = ROOT / "research" / "real-audio" / "whatsapp"
TA = ROOT / "research" / "test-audio"
DL = Path.home() / "Downloads"
TMP = Path(tempfile.mkdtemp(prefix="fpdiff_"))
_n = [0]


def ff(args, ext=".wav"):
    _n[0] += 1
    out = TMP / f"f{_n[0]}{ext}"
    subprocess.run([FF, "-v", "error", "-y", *map(str, args), str(out)], check=True)
    return out


def whatsapp(p):
    return ff(["-i", p, "-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "24k"], ".ogg")


def dur(p):
    out = subprocess.run([str(fingerprint.fpcalc_path()), "-json", str(p)], capture_output=True, text=True).stdout
    return float(json.loads(out)["duration"])


def edit(real, donor, cuts):
    """cuts: list of (kind, at, secs): replace / insert / delete, at seconds of the real clip."""
    kind, at, secs = cuts
    pre = f"[0:a]aresample=16000,aformat=channel_layouts=mono,atrim=0:{at},asetpts=N/SR/TB[a];"
    post_from = at + secs if kind in ("replace", "delete") else at
    post = f"[0:a]aresample=16000,aformat=channel_layouts=mono,atrim={post_from},asetpts=N/SR/TB[c];"
    mid = f"[1:a]aresample=16000,aformat=channel_layouts=mono,atrim=1:{1 + secs},asetpts=N/SR/TB[b];"
    if kind == "delete":
        g = pre + post + "[a][c]concat=n=2:v=0:a=1[o]"
    else:
        g = pre + mid + post + "[a][b][c]concat=n=3:v=0:a=1[o]"
    return whatsapp(ff(["-i", real, "-i", donor, "-filter_complex", g, "-map", "[o]"]))


def build_cases():
    fp = lambda p: fingerprint.compute(str(p))  # noqa: E731
    cases = []   # (label, expect, new_fp, stored_fp, truth seconds in the new clip or None)

    # ---- true copies (expect "same")
    for p in sorted(WA.glob("*.ogg")):
        s = fp(p)
        d = dur(p)
        for label, args in [("mp3 64k", ["-b:a", "64k"]), ("aac 64k", ["-c:a", "aac", "-b:a", "64k"]),
                            ("opus 16k", ["-c:a", "libopus", "-b:a", "16k"]), ("-6 dB", ["-filter:a", "volume=-6dB"]),
                            ("trim start 1.5 s", ["-ss", "1.5"]), ("trim end 2 s", ["-t", f"{d - 2:.2f}"])]:
            ext = {"mp3 64k": ".mp3", "aac 64k": ".m4a", "opus 16k": ".ogg"}.get(label, ".wav")
            pre = args[:2] if label.startswith("trim start") else []
            rest = args[2:] if pre else args
            cases.append((f"{p.stem} {label}", "same", fp(ff([*pre, "-i", p, *rest], ext)), s, None))
    # clean originals (phone recordings, studio/TTS test clips) vs heavily compressed copies:
    # the realistic "recorded clean, forwarded through WhatsApp" case
    clean = sorted((ROOT / "research" / "real-audio").glob("*.m4a")) + [TA / "spliced_en.wav", TA / "real_en.wav"]
    for p in clean:
        s = fp(p)
        for label, args, ext in [("opus 12k", ["-ac", "1", "-c:a", "libopus", "-b:a", "12k"], ".ogg"),
                                 ("opus 16k", ["-ac", "1", "-ar", "16000", "-c:a", "libopus", "-b:a", "16k"], ".ogg"),
                                 ("opus 24k", ["-ac", "1", "-c:a", "libopus", "-b:a", "24k"], ".ogg"),
                                 ("mp3 32k", ["-ac", "1", "-b:a", "32k"], ".mp3"),
                                 ("aac 32k", ["-ac", "1", "-c:a", "aac", "-b:a", "32k"], ".m4a")]:
            cases.append((f"clean {p.stem} {label}", "same", fp(ff(["-i", p, *args], ext)), s, None))
    cases.append(("clean spliced_en vs spliced_whatsapp.ogg", "same", fp(TA / "spliced_whatsapp.ogg"), fp(TA / "spliced_en.wav"), None))
    cases.append(("clean spliced_en vs spliced_whatsapp.m4a", "same", fp(TA / "spliced_whatsapp.m4a"), fp(TA / "spliced_en.wav"), None))
    for a, b in [("notice_en", "AUD-20261125-WA0012"), ("spliced_en", "AUD-20261125-WA0011"), ("clone_en", "AUD-20261125-WA0013")]:
        cases.append((f"{a} real WhatsApp copy", "same", fp(DL / "demo-clips" / f"{b}.ogg"), fp(WA / f"{a}.ogg"), None))
    orig = fp(TA / "spliced_whatsapp.mp3")
    undo = [("speed-test-2/speed_0.6x", "speed", 0.6), ("speed-test-2/speed_0.9x", "speed", 0.9),
            ("speed-test-2/speed_1.1x", "speed", 1.1), ("speed-test-2/speed_1.4x", "speed", 1.4),
            ("speed-test-2/speed_1.8x", "speed", 1.8), ("speed-test-2/tape_0.8x", "tape", 0.8),
            ("speed-test-2/tape_1.3x", "tape", 1.3), ("speed-test-2/pitch_2semitones", "pitch", -2),
            ("speed-test-2/pitch_-3semitones", "pitch", 3), ("speed-test/spliced_whatsapp_0.5x", "speed", 0.5),
            ("speed-test/spliced_whatsapp_2.0x", "speed", 2.0)]
    for name, kind, v in undo:
        src = DL / f"{name}.mp3"
        if src.exists():
            u = ff(["-i", src, "-ac", "1", "-filter:a", variants._filter(kind, v)])
            cases.append((f"undone {name}", "same", fp(u), orig, None))

    # ---- edits (expect "edited"), re-encoded like a forward
    for lang in ("en", "hi", "kn"):
        for base in ("notice", "real"):
            real, donor = WA / f"{base}_{lang}.ogg", WA / f"clone_{lang}.ogg"
            d, s = dur(real), fp(real)
            for secs in (0.5, 1, 2, 3, 5):
                for pos in (0.3, 0.65):
                    at = round(d * pos, 2)
                    cases.append((f"{base}_{lang} replace {secs}s at {at}", "edited",
                                  fp(edit(real, donor, ("replace", at, secs))), s, [at, at + secs]))
            for secs in (1, 2):
                at = round(d * 0.5, 2)
                cases.append((f"{base}_{lang} insert {secs}s at {at}", "edited",
                              fp(edit(real, donor, ("insert", at, secs))), s, [at, at + secs]))
                cases.append((f"{base}_{lang} delete {secs}s at {at}", "edited",
                              fp(edit(real, donor, ("delete", at, secs))), s, None))
            intro = whatsapp(ff(["-i", donor, "-i", real, "-filter_complex",
                                 "[0:a]aresample=16000,aformat=channel_layouts=mono,atrim=1:4,asetpts=N/SR/TB[a];"
                                 "[1:a]aresample=16000,aformat=channel_layouts=mono[b];[a][b]concat=n=2:v=0:a=1[o]",
                                 "-map", "[o]"]))
            cases.append((f"{base}_{lang} fake 3 s intro", "edited", fp(intro), s, [0, 3]))
    # edited AND sped up 1.25x, then undone like layer 5 would: judged in LOOSE mode
    for lang in ("en", "hi", "kn"):
        real, donor = WA / f"notice_{lang}.ogg", WA / f"clone_{lang}.ogg"
        d, s = dur(real), fp(real)
        for secs in (2, 3, 5, 8):
            if secs > d * 0.5:
                continue
            at = round(d * 0.4, 2)
            sped = whatsapp(ff(["-i", edit(real, donor, ("replace", at, secs)), "-filter:a", "atempo=1.25"]))
            back = ff(["-i", sped, "-ac", "1", "-filter:a", variants._filter("speed", 1.25)])
            cases.append((f"undone-edit notice_{lang} replace {secs}s at {at} (1.25x)", "edited", fp(back), s,
                          [at, at + secs]))
    for lang in ("en", "hi", "kn"):
        cases.append((f"spliced_{lang} vs notice_{lang} (insert)", "edited", fp(WA / f"spliced_{lang}.ogg"),
                      fp(WA / f"notice_{lang}.ogg"), None))

    return cases


def calibrate(cases):
    """Longest run of frames more than D below the pair's own median: true copies vs inside edits."""
    import re
    import numpy as np

    def longest(mask):
        return max((b - a for a, b in fpdiff._runs(mask)), default=0)

    pre = []
    for label, expect, nf, sf, truth in cases:
        q, s = np.asarray(nf, np.uint32), np.asarray(sf, np.uint32)
        M = fpdiff._match_matrix(q, s)
        pre.append((label, expect, truth, M, fpdiff._anchors(M)))
    for smooth in (3, 5):
        for D in (0.12, 0.16, 0.20, 0.24):
            worst, caught = {}, {}
            for label, expect, truth, M, anchors in pre:
                if not anchors:
                    continue
                best, _ = fpdiff.frame_scores(M, anchors, smooth)
                low = best < np.median(best) - D
                e = fpdiff.EDGE
                undone = label.startswith("undone")
                if expect == "same":
                    kind = ("undone" if undone else "clean->lossy" if label.startswith("clean")
                            else "WhatsApp" if "WhatsApp" in label else "re-encode")
                    worst[kind] = max(worst.get(kind, 0), int(longest(low[e:len(low) - e])))
                elif truth and ("replace" in label or "insert" in label):
                    a, b = int(truth[0] / fpdiff.FRAME_S), int(truth[1] / fpdiff.FRAME_S)
                    n = re.search(r"(replace|insert) ([\d.]+)s", label)
                    key = ("SPED " if undone else "") + f"{n[1][:3]} {n[2]}s"
                    caught.setdefault(key, []).append(int(longest(low[max(0, a - 2):b + 2])))
            print(f"smooth {smooth} D {D}: true copies' longest low run: {worst}")
            print("   edits, shortest low run inside: " + ", ".join(f"{k} {min(v)}" for k, v in sorted(caught.items())))


def main():
    cases = build_cases()
    if "--calibrate" in sys.argv:
        return calibrate(cases)
    import re
    wrong, smalls, medians, t_total = [], [], [], 0.0
    for label, expect, nf, sf, truth in cases:
        t = time.perf_counter()
        r = fpdiff.diff(nf, sf)
        t_total += time.perf_counter() - t
        if expect == "same":
            medians.append((r.typical, label))
        if expect == "edited" and re.search(r" (replace|insert|delete) (0\.5|1)s ", label):
            smalls.append(r.verdict != "same")
            print(f"{'ok ' if r.verdict != 'same' else '-- '} {label:42} below resolution, got {r.verdict}", flush=True)
            continue
        ok = (r.verdict == expect) or (expect == "edited" and r.verdict == "different")
        where = ""
        if truth and r.changed:
            hit = any(a <= truth[1] + 1 and b >= truth[0] - 1 for a, b in r.changed)
            where = " at the right place" if hit else f" WRONG PLACE (truth {truth})"
            ok = ok and hit
        if not ok:
            wrong.append(label)
        print(f"{'ok ' if ok else 'XX '} {label:42} expect {expect:6} got {r.verdict:9} shared {r.shared:.2f} "
              f"typical {r.typical:.2f} changed {r.changed} removed {r.removed}{where}", flush=True)
    same = [c for c in cases if c[1] == "same"]
    edits = [c for c in cases if c[1] == "edited"]
    print(f"\n{len(same)} true copies, {len(edits) - len(smalls)} edits >= 2 s, {len(wrong)} wrong: {wrong}")
    print(f"edits of 0.5-1 s (below resolution): {sum(smalls)} of {len(smalls)} caught anyway")
    print(f"lowest typical (median) score of a true copy: {sorted(medians)[:3]}")
    print(f"{1000 * t_total / len(cases):.1f} ms per diff")


if __name__ == "__main__":
    main()
