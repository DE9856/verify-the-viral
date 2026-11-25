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
