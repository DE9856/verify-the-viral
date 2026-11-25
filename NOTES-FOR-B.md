# Notes for Lane B (from Lane A, 2026-11-25)

Lane A's engine and web server are built on branch `lane-a` (47 tests). What that means for you:

1. **`check()` is real now**, but you can keep developing with `MOCK_ALETHEIA=cycle`. Nothing in the
   contract shape changed. See `CONTRACT.md` §6 for cache behaviour (same `id` on repeats, 0 credits).
2. **Result links work in mock mode too.** Mock results are stored, so if Lane A's server is running
   (`uvicorn app.api:app --port 8000`) and `PUBLIC_BASE_URL` points at it, the `result_url` in your
   bot replies opens a real result page with a waveform.
3. **Feedback buttons:** call `await check.send_feedback(result["operation_id"], correct)` as in the
   contract. It stores the answer and forwards it to DetectifAI; it never raises. In mock mode
   `operation_id` is `None` and it just logs.
4. **Tests:** `tests/conftest.py` (shared) gives every test its own temporary database, so your tests
   can call `check()` freely. Name yours `tests/test_bot*.py` / `tests/test_card*.py` (ownership in `CLAUDE.md`).
5. **Telegram files:** pass the downloaded file path to `check()` as-is (OGG voice note, MP4 video,
   etc.). Lane A sends voice notes to Aletheia unchanged and strips video itself. Do pass
   `tg_file_unique_id`: repeats are then answered without even opening the file.
6. **Card colours:** the result page uses red `#e5484d`, amber `#f5a524`, green `#2f9e66`. Using the
   same in `card.html`/`theme.css` keeps the card and page consistent.

## 2026-11-25 — Sync 2 passed on the demo laptop: your README claims are confirmed
Live in the test group (real API, bot + server on one laptop, ngrok https): spliced_whatsapp.ogg →
🟠 reply + card + "See where in the clip" → `/r/<id>` with one red region at 10.0–14.0 s
(truth 10.0–14.8), audio plays; 👍 stored and forwarded to DetectifAI.
- 🟡 Unclear for one isolated fake window or < 10 s scored: yes (`verdict.py`).
- Clips over 300 s: first 5 minutes checked, `trimmed: true` (your bot already prints it).
- Re-compressed repeats: Chromaprint ≥ 0.80 → same id, 0 credits (`tests/test_cache.py`).
- Idempotency-Key = sha256 of the audio we send: yes. Bonus seen today: the same voice note sent
  again within 24 h, even from another machine, was replayed by DetectifAI for 0 credits.
- `/r/<id>` timeline, red core regions, tap to play: yes (live today).
- Android share target: built, Chrome reports it installable; the on-phone test is still pending.

Small suggestion (your file, optional): the timeline button opens the page in `DEFAULT_LANG` even
after `/lang en`. The page accepts `?lang=en|hi|kn`, so `result_url + "?lang=" + lang` in `bot.py`
would open it in the chat's language.
- Update: the Android share target now passes on a real phone too (installed from the ngrok URL,
  WhatsApp-style share → result page). README can drop "pending" for the PWA.

## 2026-11-25 — default language is now English (user's call)
`config.DEFAULT_LANG` falls back to `en` and `env.example` says `DEFAULT_LANG=en`; set it in your
`.env` too. Chats that already used `/lang` keep their choice. I changed one phrase in your
`README.md` to match ("English by default"). `card.py`'s `render_card(..., lang="kn")` default is
unused (the bot always passes the chat language), so I left it.
