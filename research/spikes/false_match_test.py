"""False matches: can two DIFFERENT recordings hit the cache, plain or through layer 5 (speed/pitch)?

Run from the repo root:  PYTHONPATH=. .venv/Scripts/python research/spikes/false_match_test.py
0 credits. Uses the product code (store, fingerprint, variants) on a throwaway database.

Hard negatives (consented own voices, research/real-audio/whatsapp/ + ~/Downloads/demo-clips/):
  notice_xx vs clone_xx    same words, cloned voice          → a clone must never inherit "real"
  notice_xx vs spliced_xx  the real clip with one AI sentence → a splice must never inherit "real"
  real_xx vs notice_xx     same speaker, other words
For every ordered pair (stored A, query B) the query is sent as is, as a 1.25x speed copy and as a
+2 semitone copy. We record the best score reached at each layer, and whether it would hit (>= 0.80).
"""
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg

from app import config

TMP = Path(tempfile.mkdtemp(prefix="falsematch_"))
config.DB_PATH = TMP / "fm.db"
from app.core import fingerprint, normalize, store, variants  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FF = imageio_ffmpeg.get_ffmpeg_exe()
WA = ROOT / "research" / "real-audio" / "whatsapp"
DEMO = Path.home() / "Downloads" / "demo-clips"
CLIPS = {p.stem: p for p in sorted(WA.glob("*.ogg"))}
CLIPS.update({p.stem.replace("AUD-20261125-", "demo_"): p for p in sorted(DEMO.glob("AUD-*.ogg"))})
QUERY_FORMS = {"as is": None, "1.25x": "atempo=1.25",
               "+2 st": "aresample=44100,asetrate=44100*1.122462,aresample=44100,atempo=0.890899"}

# record the best confirmed layer-5 score (direct calls, not the 1 ms pre-screen inside generator expressions)
_best = [0.0]
_sim = fingerprint.similarity


def _recording_similarity(a, b):
    s = _sim(a, b)
    if sys._getframe(1).f_code.co_name != "<genexpr>":
        _best[0] = max(_best[0], s)
    return s


variants.fingerprint.similarity = _recording_similarity


def prepared(name, path, form):
    src = path if QUERY_FORMS[form] is None else TMP / f"{name}_{form.replace(' ', '')}.mp3"
    if QUERY_FORMS[form] is not None:
        subprocess.run([FF, "-v", "error", "-y", "-i", str(path), "-filter:a", QUERY_FORMS[form], "-b:a", "64k",
                        str(src)], check=True)
    n = normalize.normalize_sync(str(src))
    return n, fingerprint.compute(n.path)


def main():
    stored = {name: prepared(name, p, "as is") for name, p in CLIPS.items()}
    rows = []
    for (a, (na, fa)), b in itertools.product(stored.items(), CLIPS):
        if a == b:
            continue
        for form in QUERY_FORMS:
            nb, fb = prepared(b, CLIPS[b], form) if form != "as is" else stored[b]
            config.DB_PATH = TMP / f"{a}__{b}__{form.replace(' ', '')}.db"   # only A stored
            store._ready_for = None
            store.save({"id": a, "band": "no_signs"}, source={}, sha256=na.sha256, fp=fa, duration=na.duration,
                       audio_path=None)
            plain = _sim(fb, fa)
            plain_hit = store.find_similar(fb, nb.duration)
            _best[0] = 0.0
            m = variants.find(nb.path, fb, nb.duration) if not plain_hit else None
            rows.append(dict(stored=a, query=b, form=form, plain=round(plain, 3), plain_hit=bool(plain_hit),
                             layer5=round(_best[0], 3), layer5_hit=m.kind if m else None))
            print(f"{a:16} <- {b:16} {form:6} plain {plain:.3f}{' HIT' if plain_hit else '    '}  "
                  f"layer5 {_best[0]:.3f}{' HIT ' + m.kind if m else ''}", flush=True)
    (ROOT / "research" / "results" / "false_match_test.json").write_text(json.dumps(rows, indent=1))
    hits = [r for r in rows if r["plain_hit"] or r["layer5_hit"]]
    print(f"\n{len(rows)} pairs, {len(hits)} false hits")
    for r in sorted(rows, key=lambda r: -max(r["plain"], r["layer5"]))[:12]:
        print(f"  top: {r['stored']} <- {r['query']} ({r['form']}): plain {r['plain']}, layer5 {r['layer5']}")


if __name__ == "__main__":
    main()
