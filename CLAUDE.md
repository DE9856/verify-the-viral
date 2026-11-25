# Check Before Share — hackathon repo (CMRIT × DetectifAI, Track 4)

- Plan: `PLAN.md` (§5 = the two-lane split and every step's "done when"). Interface: `CONTRACT.md`.
- **Ask the user "Lane A or Lane B?" at the start of a session if they haven't said.**
- Lane A (engine + web) owns: `app/core/{normalize,aletheia,verdict,fingerprint,store,check,excerpt}.py`,
  `app/api.py`, `app/web/{result,index}.html`, `app/web/pwa/`, `app/web/static/`, `scripts/smoke_real.py`,
  `tests/test_{verdict,cache,normalize,api,excerpt}.py`.
- Lane B (bot + card + story) owns: `app/bot.py`, `app/core/card.py`, `app/web/card.html`,
  `app/web/theme.css`, `app/web/fonts/`, `app/i18n.json`, `README.md`, `submission/`,
  `tests/test_bot*.py`, `tests/test_card*.py`.
- Shared (change only together): `CONTRACT.md`, `CLAUDE.md`, `requirements*.txt`, `env.example`,
  `app/config.py`, `app/fixtures/`, `tests/test_contract.py`, `tests/conftest.py`.
- Only edit files your lane owns. Need something from the other lane? Write it in
  `NOTES-FOR-A.md` / `NOTES-FOR-B.md` and tell the user.
- Work on branch `lane-a` or `lane-b`; merge to `main` only at the sync points in `PLAN.md` §5.4.
- Develop with `MOCK_ALETHEIA` set (no credits). Use the real API only for a step's "done when" check.
- REST API in the product (`app/core/aletheia.py`). The DetectifAI MCP server is for exploring in
  Claude Code only.
- Run tests: `python -m pytest -q`. Keep `tests/test_contract.py` green on every commit.
- Secrets live in `.env` (`DETECTIF_API_KEY`, `TELEGRAM_BOT_TOKEN`). Never print, log or commit them.
- Only consented voices (our own) are recorded or cloned. No public figures.
- Facts already established (don't re-test): Aletheia returns 4 s / 2 s segments in one call; the
  overall verdict missed a spliced fake that the segments caught; Pillow can't render Kannada
  (use HTML → PNG via Playwright); Whisper is English-only for us; Telegram bots need privacy mode
  off and must be re-added to the group; bot downloads cap at 20 MB. Evidence: `research/`.
