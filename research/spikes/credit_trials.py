"""Credit-efficiency trials (PLAN step E2): real Aletheia calls with a hard budget guard.

    PYTHONPATH=. python research/spikes/credit_trials.py prepare        # build trial files (0 credits)
    PYTHONPATH=. python research/spikes/credit_trials.py plan           # list trials + estimated cost (0 credits)
    PYTHONPATH=. python research/spikes/credit_trials.py run T1a T2a    # run the named trials (costs credits)
    PYTHONPATH=. python research/spikes/credit_trials.py ledger         # what has been spent so far

Guard: a run refuses to start if the trials' estimated cost would push the total spent by this
script past BUDGET, or the account balance below RESERVE (kept for the demo + rehearsals).
Every call is logged to research/results/credit_trials.jsonl (no audio, no keys: trial id, credits,
verdicts, segment scores). Trial audio is derived from our own consented voices, so it lives in
research/real-audio/trials/ (gitignored). Calls go straight to aletheia.detect(): no app DB, no radar.
"""
import asyncio
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg

from app.core import aletheia, fingerprint, fpdiff, verdict

BUDGET = 1500                  # credits this script may spend in total (user, 2026-11-26)
RESERVE = 800                  # never let the balance drop below this
FF = imageio_ffmpeg.get_ffmpeg_exe()
WA = Path("research/real-audio/whatsapp")
TA = Path("research/test-audio")
EDIT = Path.home() / "Downloads/edit-test"
OUT = Path("research/real-audio/trials")
LEDGER = Path("research/results/credit_trials.jsonl")
EXCERPT = 10.2                 # >= RELIABLE_SPEECH_SECONDS (10 s) so our bands don't call it "unclear" for length


def ff(*args):
    subprocess.run([FF, "-v", "error", "-y", *map(str, args)], check=True, stdin=subprocess.DEVNULL)


def duration(p: Path) -> float:
    r = subprocess.run([FF, "-i", str(p), "-f", "null", "-"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    t = r.stderr.split("Duration: ")[1].split(",")[0]
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def cost(seconds: float) -> int:
    return max(20, math.ceil(2 * seconds - 1e-9))


def excerpt(src: Path, dst: Path, start: float, length: float = EXCERPT):
    ff("-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", src, "-ac", "1", "-ar", "16000", dst)


def edit_window(changed: list, total: float) -> float:
    """Start of an EXCERPT-long window centred on the changed stretches, kept inside the clip."""
    a, b = min(c[0] for c in changed), max(c[1] for c in changed)
    return round(min(max(0.0, (a + b) / 2 - EXCERPT / 2), max(0.0, total - EXCERPT)), 2)


# --------------------------------------------------------------------------- trials

def trials() -> dict:
    """id -> {idea, file, question, baseline}. Files are built by prepare()."""
    t = {
        "T1a": dict(idea="billing", file=OUT / "T1a_notice_en_plus10s_digital_silence.ogg",
                    question="Is digital silence billed? notice_en alone = 33 credits (16.4 s)",
                    baseline="charged 33"),
        "T1b": dict(idea="billing", file=OUT / "T1b_notice_en_plus10s_room_noise.ogg",
                    question="Is quiet room noise (-50 dBFS) billed?", baseline="charged 33"),
    }
    for name in ("clone_en", "clone_hi", "clone_kn"):
        t[f"T3_{name}"] = dict(idea="early-stop", file=OUT / f"T3_{name}_first10s.wav",
                               question=f"First 10 s of {name}: still overall fake?",
                               baseline="full clip: overall fake, all windows fake")
    t["T3_real_hi"] = dict(idea="early-stop", file=OUT / "T3_real_hi_first10s.wav",
                           question="First 10 s of real_hi (our hottest real voice): still real?",
                           baseline="full clip: overall real, 0/25 fake windows")
    for stem, server in [("1_replace_3s_at_2s", "partly_fake 2-6 s + 10-14 s (50 credits)"),
                         ("2_insert_2s_at_18s", "partly_fake 10-14 only, insert missed (54 credits)"),
                         ("4_replace_1s_at_20s", "partly_fake 10-14 only, swap missed (50 credits)")]:
        t[f"T2_{stem[0]}"] = dict(idea="edited-part-only", file=OUT / f"T2_{stem}_excerpt.wav",
                                  question=f"{stem}: 10 s around the changed seconds only",
                                  baseline=f"full clip on the server: {server}")
    return t


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    src = WA / "notice_en.ogg"
    opus = ["-c:a", "libopus", "-b:a", "16k", "-ac", "1", "-ar", "16000"]
    ff("-i", src, "-f", "lavfi", "-t", "10", "-i", "anullsrc=r=16000:cl=mono",
       "-filter_complex", "[0:a]aformat=sample_rates=16000:channel_layouts=mono[a];[a][1:a]concat=n=2:v=0:a=1",
       *opus, OUT / "T1a_notice_en_plus10s_digital_silence.ogg")
    ff("-i", src, "-f", "lavfi", "-t", "10", "-i", "anoisesrc=r=16000:a=0.0045:c=pink",
       "-filter_complex", "[0:a]aformat=sample_rates=16000:channel_layouts=mono[a];[1:a]aformat=channel_layouts=mono[n];[a][n]concat=n=2:v=0:a=1",
       *opus, OUT / "T1b_notice_en_plus10s_room_noise.ogg")
    for name in ("clone_en", "clone_hi", "clone_kn", "real_hi"):
        excerpt(WA / f"{name}.ogg", OUT / f"T3_{name}_first10s.wav", 0.0)
    orig_fp = fingerprint.compute(str(TA / "spliced_whatsapp.mp3"))
    for stem in ("1_replace_3s_at_2s", "2_insert_2s_at_18s", "4_replace_1s_at_20s"):
        p = EDIT / f"{stem}.mp3"
        d = fpdiff.diff(fingerprint.compute(str(p)), orig_fp)
        start = edit_window(d.changed, duration(p))
        excerpt(p, OUT / f"T2_{stem}_excerpt.wav", start)
        (OUT / f"T2_{stem}_excerpt.json").write_text(json.dumps(
            {"diff": d.verdict, "changed": d.changed, "removed": d.removed, "excerpt_start": start,
             "clip_seconds": round(duration(p), 2)}))
        print(f"{stem}: diff {d.verdict} changed {d.changed} -> excerpt {start:.2f}-{start + EXCERPT:.2f} s")
    for k, v in trials().items():
        print(f"{k:12} {duration(v['file']):5.1f} s  est {cost(duration(v['file'])):3d} credits  {v['file'].name}")


# --------------------------------------------------------------------------- run + ledger

def spent() -> int:
    if not LEDGER.exists():
        return 0
    return sum(json.loads(l).get("charged", 0) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip())


def summary(result: dict) -> dict:
    segs = result.get("segments") or []
    d = verdict.decide(result)
    return {"overall": verdict.overall_verdict(result), "score": result.get("score"),
            "duration": result.get("duration_seconds"), "scored": result.get("scored_seconds"),
            "band": d["band"], "core_regions": d["core_regions"],
            "fake_windows": [[s["start"], s["end"], round(s["score"], 3)] for s in segs if s.get("verdict") == "fake"],
            "top_score": round(max((s["score"] for s in segs), default=0), 3), "n_windows": len(segs)}


async def run(ids: list[str]):
    t = trials()
    unknown = [i for i in ids if i not in t]
    if unknown:
        sys.exit(f"unknown trials: {unknown}")
    est = sum(cost(duration(t[i]["file"])) for i in ids)
    bal = (await aletheia.credits())["available"]
    done = spent()
    print(f"balance {bal}, spent by trials so far {done}/{BUDGET}, this run est {est}")
    if done + est > BUDGET:
        sys.exit(f"REFUSED: would exceed the trial budget ({done} + {est} > {BUDGET})")
    if bal - est < RESERVE:
        sys.exit(f"REFUSED: balance would drop below the reserve ({bal} - {est} < {RESERVE})")
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for i in ids:
        p = t[i]["file"]
        key = "trial-" + hashlib.sha256(p.read_bytes()).hexdigest()
        raw = await aletheia.detect(str(p), idempotency_key=key)
        (raw_dir / f"{i}.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
        c = raw.get("credits") or {}
        row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "trial": i, "idea": t[i]["idea"],
               "file": p.name, "file_seconds": round(duration(p), 2), "charged": c.get("charged", 0),
               "balance": c.get("balance"), "replay": raw.get("idempotent_replay"),
               "question": t[i]["question"], "baseline": t[i]["baseline"], **summary(raw["result"])}
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(json.dumps(row))
    print(f"spent by trials now {spent()}/{BUDGET}")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["plan"]
    if cmd == "prepare":
        prepare()
    elif cmd == "plan":
        for k, v in trials().items():
            print(f"{k:12} est {cost(duration(v['file'])) if v['file'].exists() else '?':>3}  {v['question']}")
    elif cmd == "run":
        asyncio.run(run(rest))
    elif cmd == "ledger":
        print(f"spent {spent()}/{BUDGET}")
        if LEDGER.exists():
            print(LEDGER.read_text(encoding="utf-8"))
