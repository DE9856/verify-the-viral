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
- n = 6 recordings, male voices only, one phone, quiet room.
- WhatsApp compression simulated with ffmpeg, not WhatsApp's own encoder.

## AI clones of our own voice (truth: fake) — added 2026-11-25

Consented clones of the Script-B speaker, made locally on an RTX 5060 with open-source models:
**Chatterbox** (English) and **IndicF5** (Hindi, Kannada), each from ~10 s of the real voice
(`research/spikes/clone_handoff/`). Each clip checked clean and WhatsApp-quality.

| Clip | Overall (score) | Fake windows | Our band |
|---|---|---|---|
| clone_en — clean / WhatsApp | fake (1.000) / fake (1.000) | 7/7 / 7/7 | 🔴 likely_fake ×2 |
| clone_hi — clean / WhatsApp | fake (1.000) / fake (1.000) | 12/12 / 12/12 | 🔴 likely_fake ×2 |
| clone_kn — clean / WhatsApp | fake (0.997) / fake (0.937) | 9/9 / 8/9 | 🔴 likely_fake ×2 |

**6 / 6 caught.** WhatsApp-quality compression lowered the Kannada clone's score a little
(0.997 → 0.937) but changed no verdict.

## Spliced: real notice + one cloned sentence (the dangerous case)

Our real Script-B recording with the cloned sentence "…everyone must send five hundred rupees to this
number by tonight" pasted in at a natural pause, loudness matched (`clones/splice_truth.json`).

| Clip | Fake really at | Overall (score) | Fake windows | Our band (core region) |
|---|---|---|---|---|
| spliced_en — clean | 10.05–13.77 s | **real** (0.311) | 8–12, 10–14, 12–16 | 🟠 partly_fake **10–14 s** |
| spliced_en — WhatsApp | | **real** (0.314) | same | 🟠 partly_fake **10–14 s** |
| spliced_hi — clean | 17.95–24.48 s | fake (0.319) | 12–16, 16–26 | 🔴 likely_fake |
| spliced_hi — WhatsApp | | fake (0.387) | 14–26 | 🔴 likely_fake |
| spliced_kn — clean | 12.95–17.97 s | **real** (0.236) | 12–16, 14–18 | 🟠 partly_fake **14–16 s** |
| spliced_kn — WhatsApp | | **real** (0.233) | same | 🟠 partly_fake **14–16 s** |

**6 / 6 flagged** (none called "no signs"). What this shows:
- **English and Kannada: the overall verdict said *real* both times.** Only the 4-second windows
  caught the fake sentence, and our core-region rule put it inside the true span (English 10–14 s
  vs 10.05–13.77 s; Kannada 14–16 s vs 12.95–17.97 s, narrower than the truth).
- **Hindi:** the fake sentence is longer (6.5 s), and the overall verdict flipped to *fake* even
  though the score was only 0.32–0.39 (below the 0.62 threshold): the overall verdict isn't just
  "score > threshold". Our band then says 🔴 "likely AI-generated" for the whole clip, although the
  windows point at 16–26 s. Suggested to Lane A: show the windows' location on 🔴 too when only part
  of the clip is fake (`NOTES-FOR-A.md`).
- Compression changed nothing that matters.

Cost of the clone + splice run: 608 credits (plus ~370 wasted by an accidental re-run of the real
clips: re-encoded WhatsApp copies get new bytes, so the Idempotency-Key didn't replay them; fixed).

## Overall (n is small — say so)
| | Clips | Correct |
|---|---|---|
| Real voices (en/hi/kn, clean + WhatsApp) | 12 | 12 called real |
| Full AI clones (en/hi/kn, clean + WhatsApp) | 6 | 6 called fake |
| Real + one cloned sentence | 6 | 6 flagged (4 🟠 with the right seconds, 2 🔴) |
