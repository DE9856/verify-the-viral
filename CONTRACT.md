# CONTRACT — the only place Lane A and Lane B meet

Change this file **only together** (at a sync point, or after telling your teammate).
Everything else in a lane can change freely.

## 1. `check()` — owned by Lane A (`app/core/check.py`)

```python
async def check(audio_path: str, *, source: dict) -> dict
# source = {"channel": "telegram" | "share", "tg_file_unique_id": str | None, "filename": str,
#           "chat_id": int (optional, Telegram; only a salted hash is stored, to count chats on /radar)}
```

Returns this dict (and `POST /api/check` returns the same JSON):

```jsonc
{
  "id": "k7f3q2",                    // short id → result page at /r/k7f3q2
  "operation_id": "op_46de7281…",    // from Aletheia; used by send_feedback(); null in mock
  "model": "aletheia 2026.10",       // shown on the result page
  "band": "partly_fake",             // likely_fake | partly_fake | unclear | no_signs | error
  "overall": {"verdict": "real", "score": 0.277},
  "core_regions": [[10.0, 14.0]],    // seconds; empty unless band == partly_fake
  "segments": [{"start": 8.0, "end": 12.0, "score": 0.9999, "verdict": "fake"}],
  "duration": 24.8,
  "scored_seconds": 24.8,
  "trimmed": false,                  // true if only the first 300 s were checked
  "cache": {"hit": false, "times_checked": 1},  // on a hit of a sped-up / slowed / pitch-shifted copy,
                                     // also "variant": {"kind": "speed"|"tape"|"pitch", "speed": 1.5|null,
                                     //   "semitones": 2.5|null, "score": 0.88} (added 2026-11-25, optional)
  "credits_charged": 50,             // 0 on a cache hit or in mock mode
  // optional (added 2026-11-26): parts match a stored clip but some seconds differ (fpdiff.py), so it
  // was checked as a new clip: "edited_copy_of": {"id": "k7f3q2", "result_url": "…",
  //   "changed": [[8.0, 11.2]] (s in this clip), "removed": [[3.0, 5.0]] (s cut from the stored one)}
  "error": null,                     // or {"code": "insufficient_speech" | "too_large" | "out_of_credits" | "failed", "message": "…"}
  "result_url": "https://<PUBLIC_BASE_URL>/r/k7f3q2"
}
```

- When `band == "error"`, `overall`, `segments` and `core_regions` may be empty; read `error.code`.
- `check()` never raises for a bad clip: it returns `band: "error"`. It may raise only for
  programming errors.

## 2. `send_feedback()` — owned by Lane A (`app/core/check.py`)

```python
async def send_feedback(operation_id: str, correct: bool, label: str | None = None) -> None
# → POST /v1/operations/{operation_id}/feedback  {"correct": …, "label": "real" | "fake"}  (free)
```

## 3. `render_card()` — owned by Lane B (`app/core/card.py`)

```python
async def render_card(result: dict, lang: str = "kn") -> bytes   # PNG bytes, ~900×420
```

## 4. Wording — owned by Lane B (`app/i18n.json`)

`{"<key>": {"en": "…", "hi": "…", "kn": "…"}}`. Keys = the four band names, `error_<code>`,
plus `cache_hit`, `disclaimer`, `view_timeline`, `feedback_question`, `feedback_thanks`.
Placeholders: `{regions}`, `{n}`. Lane A's result page reads the same file, so chat and page
always say the same thing.

## 5. Mock mode (both lanes develop with it on)

`.env`: `MOCK_ALETHEIA=<fixture>` makes `check()` skip the API and return a recorded real
Aletheia result from `app/fixtures/`:

| Fixture | Expected band |
|---|---|
| `real_en` | `no_signs` |
| `fake_en`, `fake_hi`, `fake_kn` | `likely_fake` |
| `spliced_en`, `spliced_whatsapp` | `partly_fake`, core `[[10.0, 14.0]]` |
| `cycle` | rotates through all of the above, one per call |

Leave `MOCK_ALETHEIA` empty to use the real API.

Mock results are stored like real ones, so `result_url` opens a working result page (with the
fixture's real audio) whenever Lane A's server is running at `PUBLIC_BASE_URL`.

## 6. Behaviour Lane B can rely on (added 2026-11-25, no shape change)
- Same clip again (same Telegram `file_unique_id`, same bytes, the same decoded audio in another
  file — other container, lossless format, renamed or re-tagged (added 2026-11-25) — or a re-encoded
  forward with fingerprint ≥ 0.80) → the **same `id`**, `cache.hit: true`, `times_checked` + 1,
  `credits_charged: 0`.
- A copy at another speed (0.5–2×, pitch kept or changed with it) or with the voice pitch moved
  (same length) → also the original's result, plus `cache.variant`. `core_regions`, the excerpt and
  the result page stay in the **original's** seconds; the bot says so (`cache_variant_speed`,
  `cache_variant_pitch`).
- A near-match counts only if the fingerprint diff finds no changed or cut seconds (edits of ~2 s
  or more). Otherwise it's an **edited copy**: a new check (credits charged) with `edited_copy_of`,
  and the bot adds `edited_copy` / `edited_copy_cut`; in groups it's never shortened to one line.
- The diff also feeds the band (`verdict.apply_edits`, 2026-11-26): a changed stretch with >= 1
  fake segment on it becomes a core region (→ `partly_fake`); any other change or a cut turns
  `no_signs` into `unclear` with `"reason": "edited"` (texts `unclear_edited`,
  `advice_unclear_edited`). Red/orange bands keep their colour.
- Two identical clips arriving together → one API call; the second gets the cache-hit result.
- `check()` can take a few seconds on a cold API; show a "checking…" message first.

## 7. The flagged seconds as audio (added 2026-11-25, Lane A → Lane B)
```python
from app.core import excerpt
part = await excerpt.fake_part(result)   # result from check()
# None unless band == "partly_fake" and the audio is stored; else (path, [start, end]):
# an OGG/Opus file of exactly the longest core region (max 30 s), playable as a Telegram voice note.
```
Cached on disk (`data/audio/excerpts/`); calling it again for the same result is instant. The bot
sends it after the card (`send_fake_part` in `app/bot.py`).

## 9. Live listen (added 2026-11-26) — `app/core/live.py`, `GET /live`, `WS /ws/live`
Browser → server: binary frames of 16 kHz 16-bit mono PCM (~0.1 s, max 64 KB), then the text
`{"type": "stop"}`. Server → browser (JSON): `{"type": "ready"}`; `{"type": "update", "early",
"verdict": "real"|"fake", "score", "sure", "seconds", "speech_seconds", "window_seconds"}` (`sure` = score
>= `live.LIVE_MIN_SCORE` 0.9; a fake that isn't sure shows "possibly AI"); `{"type":
"limit", "seconds"}` (LIVE_MAX_SECONDS reached, default 300); `{"type": "result", "id", "band",
"core_regions", "result_url"}`; `{"type": "error", "code": "insufficient_speech" | "out_of_credits" |
"busy" | "auth" | "unavailable" | "failed"}`. The final result is stored like a check (channel
`"live"`, audio as WAV, extra field `"live": {"seconds", "speech_seconds", "updates", "ended_by"}`)
and is never listed on the radar. Its band uses `verdict.decide_live()`: a region needs >= 3
consecutive (overlapping) fake windows that each score >= 0.9; through a speaker, real speech came back
fake in 2–4 s bursts at 0.65–0.97 (`research/live-listen.md`). The page turns red only after two sure
fake updates in a row. Texts: `live_*` in `app/i18n.json`.

## 8. AI-clip radar (added 2026-11-25, Lane A)
`GET /radar` (page) and `GET /api/radar` (JSON: `items`, `stats`, `rules`). Lists real-API results
with band `likely_fake` / `partly_fake` once they are circulating: seen in ≥ 2 chats (distinct
salted chat codes; the share app counts as one) or checked ≥ 3 times, in the last 7 days. Every
`check()` and cache hit records a sighting (`sightings` table); raw chat ids are never stored.
