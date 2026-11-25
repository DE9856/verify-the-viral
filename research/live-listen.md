# Live listen: real-stream tests (2026-11-26, Fedora server, phone over ngrok)

Aletheia live stream `wss://platform.detectif.ai/v1/stream?checks=deepfake`, relayed by `app/core/live.py`.
Audio played from the laptop speaker, picked up by the phone's mic on `/live` (our own consented voice).

| Run | Played | Result | Speech | Credits |
|---|---|---|---|---|
| smoke test (file streamed through ngrok WS, no mic) | spliced_en.wav | worked; 2 updates in 25 s | — | 37 |
| Zxoudg | real_en (real voice only) | **no_signs**, 10/10 windows real (one at 0.95 still labelled real) | 20.5 s | 41 |
| o6yz8A | real notice (WA0012) → clone (WA0013) → spliced (WA0011) | overall fake 0.57 → likely_fake | 50.3 s | 101 |

Billing = 2 credits per second of speech, not per update (101 credits for 50.3 s with 5 updates).

## False alarms through the speaker (o6yz8A, aligned by speech onset: file = stream − 0.96 s)
**5 of 11 windows of only-real speech came back fake**, all at lower scores:

| Windows | Scores |
|---|---|
| real notice, file 2.4–10.4 s (3 windows) | 0.66, 0.65, 0.71 |
| real part of the spliced clip just before the AI sentence (2 windows) | 0.85, 0.65 |
| the clone (all windows fully inside it) | 0.97–1.00 |
| mostly the AI sentence | 0.98, 0.95 (0.72/0.73 when it covers < 2.2 s of it) |

Under the file-check rule (trust each window's own verdict, 2 overlapping = a region) the 3 real-notice
windows would have made a false AI region (~4.4–8.4 s), and the 2 others would have stretched the AI
sentence's region back to ~43 s.

## Rule for the live path: a fake verdict counts only at score ≥ 0.9 (`live.LIVE_MIN_SCORE`)
- Re-applied to o6yz8A's segments: **partly_fake at 22.0–32.0 s and 51.0–53.0 s (file time)** — inside
  the clone (20.4–34.7) and the AI sentence (48.8–52.5); no region in real speech. The 0.57 overall
  "fake" no longer decides on its own.
- Weaker fake windows make the result at most 🟡 unclear (never 🟢), and turn the live light to
  "possibly AI, keep listening" instead of 🔴.
- Margin: highest false alarm 0.85 vs lowest sure fake 0.95, from **one** run. Next: replay the real
  notice alone through the speaker (~35 credits) to confirm nothing goes red.
- File checks keep Aletheia's own per-window verdicts (a 0.883 Hindi window labelled real stays real).
