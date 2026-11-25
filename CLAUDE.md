# Check Before Share — hackathon repo (CMRIT × DetectifAI, Track 4)

- Plan: `PLAN.md`. Interface: `CONTRACT.md`.
- No more lanes (Lane A / Lane B ended 2026-11-25): all code changes happen on this Windows laptop;
  any file may be edited. The Fedora laptop is now the server (runs the bot + API).
- Commit and push to branch `testing`; merge `testing` into `master` only once it works
  (tests pass and it runs on the server).
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
