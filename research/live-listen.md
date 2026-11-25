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

## First rule tried: a fake verdict counts only at score ≥ 0.9 — superseded (failed on 8DezRg below)
- Re-applied to o6yz8A's segments: **partly_fake at 22.0–32.0 s and 51.0–53.0 s (file time)** — inside
  the clone (20.4–34.7) and the AI sentence (48.8–52.5); no region in real speech. The 0.57 overall
  "fake" no longer decides on its own.
- Weaker fake windows make the result at most 🟡 unclear (never 🟢), and turn the live light to
  "possibly AI, keep listening" instead of 🔴.
- Margin: highest false alarm 0.85 vs lowest sure fake 0.95, from **one** run. Next: replay the real
  notice alone through the speaker (~35 credits) to confirm nothing goes red.
- File checks keep Aletheia's own per-window verdicts (a 0.883 Hindi window labelled real stays real).

## Confirmation run 8DezRg — the 0.9 floor FAILED (2026-11-26 01:43, 33 credits)
Real notice (WA0012) alone through the speaker: partly_fake [[4.86, 6.86]]; windows 2.86–6.86 and
4.86–8.86 came back fake at **0.97** (file time ≈ 2.3–8.3 s: the same stretch that scored 0.65–0.71
in o6yz8A). Overall real 0.37. The score of this false alarm varies run to run, so a score floor
tuned on one call cannot filter it (overfitting). Open question: does a plain FILE check of WA0012
flag 2–8 s too (recording vs speaker path)? Candidate rule: sustained evidence on the live path
(≥ 3 overlapping confident windows ≈ 8 s), since a live threat is a cloned caller, not a 2 s splice.

## Recording or speaker? (0 credits) — the speaker path
WA0012 is the same recording as `notice_en` (fingerprint 0.965, `false-match.md`), which Aletheia
checked as a FILE in the accuracy test: clean → windows 2–6 s real 0.079, 4–8 s real 0.005, overall
real 0.02; WhatsApp quality → 2–6 s real **0.173**, overall real 0.03. So the file is clean (the demo
video's real clip is safe); playing it through a speaker pushes its weakest stretch to fake
(0.65–0.71, then 0.97). Note: with 4 s windows every 2 s, at most 2 windows cover any moment, so a
"sustained" rule must count CONSECUTIVE confident fake windows (≥ 3 ≈ 8 s), not overlaps.

## Rule now: sustained + confident (`verdict.decide_live`, 2026-11-26)
A region needs ≥ 3 consecutive (overlapping) fake windows that each score ≥ 0.9 (≈ 8 s); likely_fake
also needs a confident (≥ 0.9) overall fake; any weaker fake signal → unclear, never green. The live
light turns red only after 2 sure fake updates in a row. On the three calls: Zxoudg → no_signs;
8DezRg (2 windows at 0.97) → unclear; o6yz8A → partly_fake [[22.99, 32.99]] (stream time; the clone,
file 22.0–32.0 inside 20.4–34.7), no longer marking the 3.7 s AI sentence (file checks do that).
Still 3 calls: needs more REAL voices through the speaker (hi, kn, other speakers) before trusting it.
Bug caught by the tests: "in a row" must mean overlapping, not "starts ≤ 2.5 s apart" — Aletheia
stretches a window across silence (17.31–24.99).

## Real-voice runs on the sustained rule (d6b9ab0, 2026-11-26 01:55–01:56) — PASS
| Id | Voice (through the speaker) | Band | Overall | Windows | Highest window | Credits |
|---|---|---|---|---|---|---|
| zpUIdA | real Hindi (real_hi, 51 s) | no_signs | real 0.41 | 21, all real | 0.87 (real) | 87 |
| cw9OSw | real Kannada (real_kn, 35 s) | no_signs | real 0.12 | 15, all real | 0.70 (real) | 64 |
| DqlAmg | real English notice (WA0012) again | no_signs | real 0.41 | 7, all real | **0.91 at 5.25–9.25 (real)** | 31 |
| 0iXNcA | false start, 2.8 s | no result (insufficient_speech), not stored | — | — | — | 0 |

No fake window in any run, so these don't stress the rule; they show the speaker path doesn't
always misfire. The notice's 2–8 s weak spot recurs (0.65–0.71, 0.97, now 0.91 labelled real): the
rule's protection rests on 8DezRg. Live-listen testing total: ~394 credits.
Tally so far through the speaker: real voices 5 calls (en ×3, hi, kn) → 4 no_signs + 1 unclear, 0 red;
clone 1 call → caught.
