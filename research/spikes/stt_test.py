"""Idea 1 stretch: word timestamps so we can highlight the faked sentence. CPU only."""
import json, time, sys
from faster_whisper import WhisperModel
res = json.loads(json.load(open("results/spliced_en.json", encoding="utf-8"))["result"]["content"][0]["text"])["result"]
# per-second max score from overlapping segments
fake_spans = [(s["start"], s["end"]) for s in res["segments"] if s["verdict"] == "fake"]
lo, hi = min(a for a, b in fake_spans), max(b for a, b in fake_spans)
for size in sys.argv[1:]:
    t0 = time.time(); m = WhisperModel(size, device="cpu", compute_type="int8"); tl = time.time() - t0
    for f, lang in (("audio/spliced_en.wav", None), ("audio/fake_hi.mp3", None), ("audio/fake_kn.mp3", None)):
        t0 = time.time()
        segs, info = m.transcribe(f, language=lang, word_timestamps=True, beam_size=1)
        words = [w for s in segs for w in s.words]
        dt = time.time() - t0
        text = "".join(w.word for w in words)
        print(f"[{size}] {f}: lang={info.language}({info.language_probability:.2f}) {dt:.1f}s (load {tl:.1f}s)")
        print("   ", text[:200])
        if "spliced" in f:
            # words whose midpoint is inside the flagged window (8-16s), but 'core' = covered by >=2 fake windows
            core = [w.word for w in words if sum(a <= (w.start+w.end)/2 <= b for a, b in fake_spans) >= 2]
            print("    flagged words (>=2 fake windows):", "".join(core))
