# False matches in the "already checked" cache (2026-11-25, 0 credits)

Question: can two *different* recordings hit the cache, so one inherits the other's verdict?
Audio: our consented recordings in `research/real-audio/whatsapp/` (real, notice, clone of notice,
notice with an inserted AI sentence; en/hi/kn) + the real-WhatsApp demo copies in ~/Downloads/demo-clips.

## 1. All pairs, plain fingerprint + layer 5 — `spikes/false_match_test.py`
630 ordered pairs (each query as is, 1.25×, +2 semitones). Raw: `results/false_match_test.json`.
- 612 different-recording pairs: **0 hits**. Highest: notice vs its inserted-sentence splice 0.744
  (plain), 0.734 (layer 5). Clone reading the same words vs the real: ≤ 0.59.
- 18 same-recording pairs (phone WhatsApp copies of notice/spliced/clone_en): 18 hits, ≥ 0.914.
- Layer 5's extra tries did not raise any different-recording score above the plain layer's.

## 2. Replacement splices — `spikes/replace_splice_test.py`  ⚠ real gap (pre-dates layer 5)
N seconds of the notice replaced by N seconds of its clone (same length, rest stays aligned):

| Clip | 2 s | 3 s | 5 s | 8 s |
|---|---|---|---|---|
| notice_en (16 s) | 0.904 | 0.867 | 0.805 | 0.684 |
| notice_hi (33 s) | 0.963 | 0.947 | 0.919 | 0.865 |
| notice_kn (25 s) | 0.954 | 0.935 | 0.893 | 0.837 |

≥ 0.80 = cache hit: a fake replacing up to ~30 % of a known clip gets the real one's verdict (or the
reverse). The score is a whole-clip average, so a few fake seconds are averaged away.

## 3. Fix candidate: worst 2-second window — `spikes/window_min_test.py`
At the best alignment, score 16-frame (~2 s) windows and take the worst:
- same recording: real WhatsApp copies 0.943–0.953, re-encodes 0.766–0.768, layer-5 undone copies
  0.668 (1.8×) – 0.982
- splices: replacement 0.422–0.598, insertion 0.512

Gap between 0.598 and 0.668: requiring worst window ≥ ~0.63 on top of the average ≥ 0.80 would
block every splice here and keep every true copy. Small margin at 1.8×.

**Built instead (2026-11-26): the fingerprint diff, `fp_diff.md`** — finds *which* seconds differ,
calibrated on 128 true copies + 105 edits; every edit ≥ 2 s refused as a cache hit.
