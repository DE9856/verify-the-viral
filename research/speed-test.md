# Speed-changed copies of one clip (2026-11-25)

Fedora server, branch `testing` @ 276fd58, real API. Source: `research/test-audio/spliced_whatsapp.mp3`
(24.8 s, original check 4fk9JQ = partly_fake, fake part 10–14 s; truth 10.05–13.77 s).
Copies made with ffmpeg `atempo` (tempo changed, **pitch kept**), 64k MP3, sent to the bot as files.

| Speed | Length | Cache | Fingerprint vs original | Result | Flagged | Mapped back to original | Credits |
|---|---|---|---|---|---|---|---|
| 0.5× | 49.57 s | miss | 0.534 | likely_fake (overall fake 0.63, 14/24 windows fake) | — | — | 100 |
| 0.75× | 33.06 s | miss | 0.570 | partly_fake | 14–18 s | 10.5–13.5 s ✓ | 67 |
| 1.25× | 19.85 s | miss | 0.604 | partly_fake | 8–10 s | 10–12.5 s ✓ | 40 |
| 1.5× | 16.54 s | miss | 0.567 | partly_fake | 6–8 s | 9–12 s ✓ | 34 |
| 1.75× | 14.18 s | miss | 0.549 | partly_fake | 6–8 s | 10.5–14 s ✓ | 29 |
| 2.0× | 12.40 s | miss | 0.537 | unclear (1/6 windows fake) | — | — | 25 |

Total 295 credits.

## Findings
- **Cache:** no speed change is recognised. Most are excluded by the length filter in
  `store.find_similar` (±max(3 s, 15 %)); the rest score 0.53–0.60, i.e. chance (0.5), far below
  0.80. Chromaprint compares fixed time frames, so a tempo change breaks alignment.
- **Detection, 0.75×–1.75×:** holds. All four partly_fake, every region maps onto the real fake part.
- **0.5×:** whole clip called fake (real parts too). Not yet known whether a fully *real* clip at
  0.5× is also called fake (next test: `real_en.wav` at 0.5×, ~100 credits).
- **2×:** fake part shrinks to ~2 s, only one 4 s window flags it → unclear (our 2-window rule).

## Options considered (not built)
- Speed-tolerant cache: on a miss, fingerprint the clip at a few tempo corrections and compare
  against stored clips of the matching length. Extra fpcalc runs; the 0.80 threshold would need
  re-testing for false matches.
- Unnatural-speed guard: estimate speech rate, and say "unclear, speed looks altered" at extremes
  instead of trusting likely_fake.

## Offline matching test (0 credits) — `research/spikes/speed_fp_test.py`
Stored: spliced_whatsapp.mp3, real_en, fake_en/hi/kn. Queries: spliced at 0.5–2× (tempo, pitch kept),
spliced at 0.75/1.25/1.5× with pitch shifted (asetrate), spliced 1.5× + 3 s trimmed, real_en at
0.75/1.25/1.5/2×, fake_en at 1.25/1.5×. 81 pairs (17 same clip, 64 different). Raw: `results/speed_fp_test.json`.

| Method | Same clip, tempo copies (min) | Same clip, pitch-shifted (min) | Different clip (max) | ms / pair |
|---|---|---|---|---|
| plain Chromaprint (today) | 0.534 | 0.535 | 0.615 | — |
| A stretch the stored fingerprint | 0.631 (0.658 without trim) | 0.550 ✗ | 0.667 | 1.3 |
| B undo speed with ffmpeg at the length ratio | 0.619 trim ✗ (0.838 without) | 0.981 (if pitch mode used) | 0.667 | 109 |
| C fusion: A sweeps speeds, B confirms top 2 | 0.788 trim (0.831 without) | 0.538 ✗ | 0.652 | 317 |
| C2 fusion v2: B at length ratio in both modes + B at A's refined peak | 0.797 trim (0.838 without) | 0.981 | 0.667 | 336 |

- B/C2 bring every untrimmed speed copy (0.5–2×, both modes) to ≥ 0.838; different clips stay ≤ 0.667.
- A alone never reaches 0.80, but it ranks well: as a gate at 0.62 it passes every tempo copy and
  only 1 of 64 different-clip pairs, in ~1 ms. It can't see pitch-shifted copies.
- Trim + speed: only the fusions find the right speed (1.485); 0.797 is the partial-overlap penalty
  in `similarity()` (3 s of 24.8 s missing), the same penalty a 3 s trim gets at 1×.

## Pitch changes (0 credits)
**Tape-style (speed + pitch together, asetrate), `speed_fp_test.py`:** spliced at all six speeds,
real_en at 0.75/1.5/2×. Undoing at the length ratio in pitch mode (B/C2): **0.951–0.994** for every
copy. A (fingerprint stretch) can't see these (≤ 0.73), so tape-style + trim is **not** found (0.555).

**Pure pitch shift (same length, `pitch_fp_test.py`):** spliced and real_en shifted −4…+4 semitones,
including 0.5, 2.5 and 3.3. Plain Chromaprint 0.54–0.81 (only ±0.5 semitone scrapes through).
Undo grid of whole semitones: 0.87–0.95 on whole shifts but 0.77–0.79 on half shifts ✗. Undo grid
of **half semitones (±6, 24 tries): every copy 0.861–0.970**; different clips ≤ 0.652 across all 24 tries.
Cost: the tries are on the new clip, not per stored clip (~0.2 s each → ~5 s for 24 if run one
after another).

## Built (2026-11-25): `app/core/variants.py`, cache layer 5
All three kinds (speed, tape, pitch), as above: speed copies pre-screened by the stretched
fingerprint (≥ 0.62) then undone at the best speed and at the length ratio; tape copies undone at
the length ratio (most-checked 8 clips); pitch copies undone at −6…+6 semitones in parallel, then
±0.5 next to the best if it scored ≥ 0.70. Match = 0.80 as before. A hit returns the original's
result plus `cache.variant`; the bot adds "This is a 1.5× speed copy … times refer to the original".
Cost on a miss: ~1–1.2 s with 5 stored clips (Windows laptop, 8 parallel ffmpeg runs).
Tests: `tests/test_cache.py` (1.5×, 0.5×, tape 1.25×, +2.5 semitones match; real_en 1.25× doesn't).
