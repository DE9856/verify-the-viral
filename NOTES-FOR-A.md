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

## 2026-11-25 — spliced Hindi clip: overall "fake" at score 0.32 (affects verdict.py, optional)
Real Hindi notice + 6.5 s cloned sentence at 17.95–24.48 s: Aletheia's overall verdict was **fake**
with score 0.319 (threshold 0.62); windows flagged 12–26 s. Our band → 🔴 likely_fake for the whole
clip, so the timeline/"which seconds" is lost. Idea: when overall is fake but under ~half the
windows are fake, keep `core_regions` (or return partly_fake). Details: `research/real-world.md`.

## 2026-11-25 — UI redesign touched your pages (user's call: one new look everywhere)
New "ticket" look across card, `result.html` and `index.html`. What changed on your side:
- Fonts moved to `app/web/static/fonts/`; shared stylesheet is now `app/web/static/theme.css`
  (served at `/static/theme.css`, also used by the card). Old `app/web/theme.css` + `app/web/fonts/` are gone.
- `result.html`: same data slots (`__LANG__`, `__DATA__`, `__I18N__`), manifest link with
  `crossorigin="use-credentials"`, `/media/<id>`, `/api/feedback/<id>` and wavesurfer 7.12.12 all kept.
  New: per-second "stages" you can tap to hear, "Hear the AI-sounding part" button, all labels from
  `i18n.json` (new `page_*` keys, `label_error`). Kept your `?lang=` support.
- `index.html`: same form (`/share`, field `media`), service worker registration and manifest link.
- `manifest.webmanifest`: only `background_color` / `theme_color` changed to the new palette.
- Bot timeline button now adds `?lang=<chat language>` (your suggestion).
- `radar.html` (now "AI-clip radar") redesigned in the same ticket look (2026-11-25): your polling, `/api/radar` data use,
  privacy text and "+N" bump logic are unchanged; each clip is now a ticket in its verdict colour with
  a "×N in M chats" stub that gets re-punched when the count grows. Landing page radar link kept (new style).
