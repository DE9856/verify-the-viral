# Real-world accuracy test (Day 0, D3) — 2026-11-25

Our own voices (one male speaker per clip, with consent), recorded on a phone voice-recorder app
(HE-AAC 48 kHz, 16–51 s). Each clip was sent twice: the clean file, and a WhatsApp-quality copy
(Opus, mono 16 kHz, 16 kb/s, made with ffmpeg; this only approximates WhatsApp's own encoder).
REST API `POST /v1/deepfake/detect`, model `aletheia 2026.10`. Script: `research/spikes/real_world_test.py`.
Scripts read aloud: `research/script.md`. Audio + raw JSON: `research/real-audio/` (gitignored, not public).

## Real voices (truth: real)

| Clip | Length | Overall (score) | Top segment score | Fake windows |
|---|---|---|---|---|
| real_en — clean | 21 s | real (0.010) | 0.017 | 0 / 10 |
| real_en — WhatsApp | | real (0.020) | 0.056 | 0 / 10 |
| real_hi — clean | 51 s | real (0.186) | **0.883** | 0 / 25 |
| real_hi — WhatsApp | | real (0.160) | **0.845** | 0 / 25 |
| real_kn — clean | 35 s | real (0.024) | 0.121 | 0 / 17 |
| real_kn — WhatsApp | | real (0.041) | 0.164 | 0 / 17 |
| notice_en — clean | 16 s | real (0.021) | 0.079 | 0 / 8 |
| notice_en — WhatsApp | | real (0.029) | 0.173 | 0 / 8 |
| notice_hi — clean | 33 s | real (0.163) | 0.626 | 0 / 16 |
| notice_hi — WhatsApp | | real (0.235) | 0.672 | 0 / 16 |
| notice_kn — clean | 26 s | real (0.072) | 0.156 | 0 / 12 |
| notice_kn — WhatsApp | | real (0.087) | 0.258 | 0 / 12 |

**False alarms: 0 of 12** (0 of 145 segment windows marked fake). Cost: 734 credits (5,000 → 4,266).

## What we learned
- **Kannada is fine** on our voices: scores as low as English (top segment ≤ 0.26). The open
  question "Kannada false-alarm rate" is answered for n = 2 Kannada clips: none.
- **Hindi runs hottest.** Overall scores 0.16–0.24 and single windows up to **0.88**, still
  labelled `real`. Hindi is the language closest to a false alarm, not Kannada.
- **Segment verdicts do not use the overall threshold (0.62).** A window scored 0.883 came back
  `verdict: "real"`. So the verdict logic must read each segment's `verdict` field, never
  `score > 0.62`. (Told Lane A in `NOTES-FOR-A.md`.)
- WhatsApp-quality compression nudges scores up slightly (e.g. notice_en top 0.08 → 0.17) but
  changed no verdict.

## Limits (say these in the README)
- n = 6 recordings, male voices only, 2 speakers, one phone, quiet room.
- WhatsApp compression simulated with ffmpeg, not WhatsApp's own encoder.

## Still to test
- `clone_en`: AI clone of the notice_en speaker reading Script B → should be `fake`.
- `spliced_en`: notice_en with one cloned sentence pasted in at ~10 s → overall may say real;
  the segments should flag only the pasted seconds.
