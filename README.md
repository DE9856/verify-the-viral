# Check Before Share

*(working name)* — a Telegram group guardian and Android share-sheet app that checks voice notes
and videos with **DetectifAI's Aletheia** deepfake model, shows **which seconds** sound
AI-generated, and returns a forwardable verdict card. CMRIT × DetectifAI hackathon, Track 4
(Verify the Viral).

> Lane B rewrites this README for submission (step B5). This version is the team setup guide.

## Why the timeline matters
In our tests, a real recording with one AI sentence spliced in got an overall verdict of
**real** (score 0.28). Aletheia's per-segment scores flagged exactly that part (10–14 s),
even after WhatsApp-grade compression. Evidence: `research/`.

## Setup (both teammates)
```bash
git clone <repo-url> && cd <repo>
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp env.example .env          # then fill in your keys (never commit .env)
python -m pytest -q          # contract tests pass; verdict tests skip until step A2
```
Chromaprint `fpcalc` (Lane A, step A3): download 1.5.1 from
https://github.com/acoustid/chromaprint/releases, put it in `bin/`, set `FPCALC_PATH` in `.env`.

## Run
```bash
python -m scripts.credits          # Day 0: check your API key + balance
python -m app.bot                  # Telegram bot (Lane B)
uvicorn app.api:app --port 8000    # web server + result pages + PWA (Lane A)
```
With `MOCK_ALETHEIA=cycle` in `.env`, everything runs on recorded real results and uses no credits.

## How the work is split
Two lanes, joined by `CONTRACT.md`. Lane A: engine + web. Lane B: bot + card + story.
Steps and "done when" checks: `PLAN.md` §5. Rules for Claude Code sessions: `CLAUDE.md`.

## DetectifAI usage
- Product: REST API `POST /v1/deepfake/detect` (one call per clip; the response includes
  4-second segment scores) and `POST /v1/operations/{id}/feedback` for users' 👍/👎.
- Development: DetectifAI MCP server inside Claude Code for exploring results.
