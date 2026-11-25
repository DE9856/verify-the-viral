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
