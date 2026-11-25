# CONTRACT — the only place Lane A and Lane B meet

Change this file **only together** (at a sync point, or after telling your teammate).
Everything else in a lane can change freely.

## 1. `check()` — owned by Lane A (`app/core/check.py`)

```python
async def check(audio_path: str, *, source: dict) -> dict
# source = {"channel": "telegram" | "share", "tg_file_unique_id": str | None, "filename": str}
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
  "cache": {"hit": false, "times_checked": 1},
  "credits_charged": 50,             // 0 on a cache hit or in mock mode
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
- Same clip again (same Telegram `file_unique_id`, same bytes, or a re-encoded forward with
  fingerprint ≥ 0.80) → the **same `id`**, `cache.hit: true`, `times_checked` + 1, `credits_charged: 0`.
- Two identical clips arriving together → one API call; the second gets the cache-hit result.
- `check()` can take a few seconds on a cold API; show a "checking…" message first.
