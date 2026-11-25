# Fingerprint diff (`app/core/fpdiff.py`), 2026-11-26, 0 credits

Why: a whole-clip fingerprint score is an average, so a fake replacing up to ~30 % of a known clip
still scored ≥ 0.80 and would have inherited that clip's verdict (`false-match.md`). The diff lines
the two clips up piece by piece and lists the seconds that don't match; only "nothing changed" is a
cache hit. Used by layer 4 (plain fingerprint) and layer 5 (after a speed/pitch undo).

## How it works
Every frame (~0.124 s) of the new clip vs every frame of the stored one → strong ~2 s diagonals =
candidate alignments (one for a copy; two or more around an insertion or a cut) → each new frame
takes its best alignment (5-frame average) → a frame is **unmatched** when it scores more than 0.24
below the pair's own median → 3+ unmatched frames in a row = changed; a 5+ frame gap in the stored
clip between matched parts = cut. Also: median < 0.75 → never "same" (when half a clip is replaced
the median itself sinks into the fake's range).

Why relative to the median: heavy compression (clean recording → 12–16 kbps Opus) lowers the whole
clip and dips ~1 s at a time. A fixed threshold either flagged those copies as edited (first
version: the clean-WAV vs 16 kbps-Opus unit test failed) or missed 2–3 s fakes.

## Test set — `spikes/fp_diff_test.py` (results: `results/fp_diff_test.txt`)
Consented own voices (en/hi/kn, real + notice + clone of the notice as the fake donor: same voice,
same words, the hardest case), research test clips, real phone-WhatsApp copies, speed/pitch copies.

| Group | Cases | Result |
|---|---|---|
| True copies: re-encodes (mp3/aac/opus), −6 dB, trims, clean → 12/16/24 kbps Opus / 32 kbps mp3+aac, real WhatsApp forwards, undone speed 0.5–2× / tape / pitch copies | 128 | **128 "same"** (lowest median 0.869) |
| Edits ≥ 2 s: replace 2/3/5 s at two places, insert 2 s, cut 2 s, fake 3 s intro, inserted-sentence splices, edited **and** sped up 1.25× (2/3/5/8 s) | 69 | **69 "edited", at the right seconds** |
| Edits of 0.5–1 s | 36 | 27 caught anyway; below the stated resolution |

7 ms per diff.

## Limits (honest)
- **Resolution ~2 s.** A fake of ~1 s or less (one swapped word) can pass as the same clip. Next
  step if needed: a transcript veto for English (`false-match.md` option 4).
- Tuned on 3 speakers (all male), 3 languages, our codecs. A larger synthetic set from public
  speech corpora (option 7) is the way to set these numbers with a real margin.
- Fails safe where it can: a wrongly flagged "edited" only costs one Aletheia check.

## Server test (Fedora, 8d0ebff, clean test DB, 2026-11-26 00:49) — real API
Original spliced_whatsapp.mp3 stored as LmBubg (partly_fake 10–14 s). Files in ~/Downloads/edit-test,
donor = fake_en.mp3 (Edge TTS, i.e. AI speech):

| File | Edit | Diff (server) | Aletheia band | Credits |
|---|---|---|---|---|
| 5_control_reencode_only | 16 kbps Opus, no edit | same → cache hit | (stored) partly_fake 10–14 | 0 |
| 1_replace_3s_at_2s | 2–5 s → TTS | changed 1.2–4.6 s | partly_fake **2–6 s** + 10–14 s | 50 |
| 2_insert_2s_at_18s | +2 s TTS at 18 s | changed 16.6–19.2 s | partly_fake 10–14 only — **missed the insert** | 54 |
| 3_cut_3s_at_16s | 16–19 s cut | cut 15.4–18.2 s | partly_fake 10–14 | 44 |
| 4_replace_1s_at_20s | 20–21 s → TTS | changed 19.0–20.6 s | partly_fake 10–14 only — **missed the swap** | 50 |

Before the diff all four edits would have been cache hits (whole-clip 0.85–0.97) with LmBubg's result.
**Aletheia did not flag the 1–2 s AI pieces** (our partly-fake rule needs 2 overlapping 4 s windows);
for those, the diff's "edited copy, 17–19 s / 19–21 s are different" was the only warning. Changed
regions land ~0–0.8 s early (smoothing). Next step idea: make the band reflect a diff-found change.
