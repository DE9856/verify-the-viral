# Credit-efficiency trials (step E), 2026-11-26

Goal (user): make the product credit-efficient. Safe savings get built; risky ideas get trial and
error with a hard budget (1,500 credits, balance never below 800). Script with the guard + ledger:
`spikes/credit_trials.py`; real-pipeline check: `spikes/edit_copy_e2e.py`; every call is logged in
`results/credit_trials.jsonl`. Audio = our own consented voices (`real-audio/`, not in git).
**Spent: 476 credits** (balance 12,023 → ~11,547).

## What we learned about billing (from the replies, 0 extra credits)
- Charge = `ceil(2 × duration)`, minimum 20 (10 s). 14.28 s → 29, 20.447 s → 41, 50.688 s → 102.
- **Silence in a file is billed.** notice_en (16.4 s, 33 credits) + 10 s digital silence → 53;
  + 10 s quiet room noise → 53. `scored_seconds` = the whole file. (Live listen differs: speech only.)
- Same bytes within 24 h = replay, 0 credits (`idempotent_replay`).

## Trials
| Idea | Test | Credits | Result |
|---|---|---|---|
| Billing | T1a/T1b: +10 s silence / room noise | 106 | both billed in full; verdicts unchanged (real) |
| Early stop | T3: first 10 s of clone_en/hi/kn | 63 | all 3 already overall **fake**, every window fake |
| Early stop | T3: first 10 s of real_hi (our hottest real voice) | 21 | real, top window 0.16: no false alarm |
| Edited part only | T2: 10 s around the changed seconds of 3 edited copies | 63 | same answer as the full check or better (below) |
| Edited part only, end to end | original + 4 edited copies through `check()`, fresh DB | 63 | **63 credits instead of 198**, answers below |

End to end (`edits.py` in the real pipeline; full check = server test of 2026-11-26):

| Edited copy | Mode | Credits (full check) | Answer (full check) |
|---|---|---|---|
| 1 replace 3 s at 2 s | excerpt 0–10.2 s | **21** (50) | partly_fake 2–6 + 10–14 (same) |
| 2 insert 2 s AI at 18 s | excerpt 12.8–23 s | **21** (54) | partly_fake 10–12.8 + **16.6–22.8** (full check **missed** the insert) |
| 3 cut 3 s at 16 s | cut | **0** (44) | partly_fake 10–14 (same) |
| 4 replace 1 s at 20 s | excerpt 14.6–24.8 s | **21** (50) | partly_fake 10–14 (same; the 1 s swap is missed by both) |

Why the excerpt caught what the full clip missed: in a shorter clip the AI seconds weigh more in
each window's context. One small cost: an original fake region that runs into the excerpt is cut
at the excerpt's edge when the excerpt itself only has one fake window there (copy 2: 10–12.8
instead of 10–14).

## Edge silence (built after the trials above)
Silence before the first and after the last sound is cut from the copy we SEND (stream copy, no
re-encode; the stored and played file stays whole; Aletheia's times are shifted back). Only when it
saves >= 2 credits and >= 10.5 s remain. Real API, clips padded with 2 s of room noise at both ends:

| Clip | Untrimmed price | Charged | Answer |
|---|---|---|---|
| spliced_en, first version (start cut 1.84 s) | 49 | 44 | partly_fake but **13.8–15.8 s** (2 windows): narrower |
| spliced_en, start cut in whole 2 s steps | 49 | **46** | partly_fake **12–16 s**, the same 3 windows as the original (10–14 + 2 s pad) |
| notice_hi (our hottest real voice) | 75 | 70 | no_signs, 0 fake windows (same) |

Lesson: Aletheia's 4 s windows start every 2 s from 0, so cutting the start by anything other than
whole 2 s steps moves the windows and can change a region. The start is now cut in 2 s steps only;
the end can be cut freely (only the last window changes). Our recorded clips have <= 1.1 s at the
edges, so they are sent unchanged; the saving is for voice notes with dead air at either end.
**Trial spend total: 476 credits.**

## Decisions
- **Built (`app/core/edits.py`, `check._check_edited`):** an edited copy of a known clip pays
  only for its new seconds. Cut-only copy → 0 credits (original's result on the new timeline,
  never 🟢). Copy of a 🔴 clip → 0 credits (at least half of it is that AI audio). One changed
  stretch (insert or in-place replacement) → ~10 s excerpt (21 credits). Anything else → whole
  clip, as before. Every edited copy still says which seconds differ.
- **Not built: cutting pauses.** Our real voice notes have little silence: pauses ≥ 0.7 s are
  0–6 % of a clip, 0–10 % even at 0.25 s pauses (with 2–12 extra joins each, which could look like
  splices). Not worth the false-alarm risk or the timeline remapping. Leading/trailing silence was
  ≤ 1.1 s (≤ 2 credits). Worth revisiting only for real-world clips with long silences.
- **Next, if time: early stop for long clips.** The first 10 s of every clone was already clearly
  fake. For a clip > ~60 s: check the first 10 s; if every window is fake, stop (a fully cloned
  3-minute clip: 21 credits instead of 360); else check the rest from 8 s on (~5 extra credits
  for a real clip). Needs a merge of the two segment lists and a test on a long clip.
- **Rejected:** speeding audio up before sending to pay for fewer seconds (games the pricing,
  changes what the model hears).
