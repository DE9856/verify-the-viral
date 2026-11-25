# Notes for Lane A (from Lane B)

## 2026-11-25 — segment verdicts use their own threshold (affects A2 `verdict.py`)
In our real-voice test (`research/real-world.md`) a Hindi segment scored **0.883** and still came
back `"verdict": "real"`, while the overall threshold in the response is 0.62. So in `verdict.py`
decide "fake window" by each segment's `verdict` field, not by `score > threshold`.
Also: 0 false alarms on 12 real clips (en/hi/kn, clean + WhatsApp-quality); Hindi runs hottest.

## 2026-11-25 — README claims that depend on Lane A (please confirm at Sync 2)
`README.md` (draft) says, marked *(Sync 2)* where not built yet:
- 🟡 Unclear when there is one isolated fake window **or < 10 s of speech** (PLAN §3).
- Clips over 300 s: we check the first 5 minutes and say so (`trimmed`).
- "Already checked N times" survives WhatsApp re-compression (Chromaprint ≥ 0.80), 0 credits.
- Idempotency-Key = sha256 of the normalised audio.
- `/r/<id>` timeline: red core regions, click to play the fake part.
- Android share target (PWA).
If any of these change or get cut, tell Lane B so the README stays honest.

## 2026-11-25 — Sync 1: done from your NOTES-FOR-B
- Bot shows "⏳ Checking…" if check() takes > 1.5 s, deleted when the answer arrives.
- Card uses your red `#e5484d` and green `#2f9e66`. Suggestion: the chat text says 🟠 for
  partly_fake, so the card uses orange `#f76b15` for it (yellow `#eab308` for unclear). If you
  agree, use orange for partly_fake on `result.html` too, so chat, card and page match.
