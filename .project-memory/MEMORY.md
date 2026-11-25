# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Lane A engine + web built on branch `lane-a` (`app/core/*`, `app/api.py`, result page, PWA); Lane B modules (`bot.py`, `card.py`) still stubs. Python 3.11, FastAPI, python-telegram-bot. Tests: `python -m pytest -q`.

## Current work
- Goal: build Track 4 "Check Before Share" (ideas 1+3+4+6+7, Aletheia only) at the hackathon; team of 2, each with Claude Code.
- Plan: `PLAN.md` §5 (Lane A engine+web, Lane B bot+card+story; interface in `CONTRACT.md`, session rules in `CLAUDE.md`); status in `.project-memory/PLAN.md`.
- Done: research; scaffold on master; Lane A A1–A5 + A7 on `lane-a` (47 offline tests, browser e2e, Chrome installability OK). See `PLAN.md` §5.7.
- In progress: none (Lane A pushed to origin/lane-a).
- Next: 1) user: `.env` with DETECTIF_API_KEY → `python -m scripts.smoke_real` (≈200 credits, expect ALL GOOD) 2) ngrok static domain + PUBLIC_BASE_URL → `/health` clean 3) Android install/share test; Lane B starts B1 (see `NOTES-FOR-B.md`); A6 transcript optional.
- Blockers / open questions: confirm lane split (rec: this PC = A, teammate = B); build hours; who has the Android phone; credit balance; Kannada false-alarm rate.
- Updated: 2026-11-25, Claude

## Rules & gotchas
- Run tests with the repo venv: `.venv/Scripts/python -m pytest -q`. `fpcalc.exe` lives in `bin/` (gitignored).
- Voice notes are sent to Aletheia unchanged (passthrough); only odd formats are transcoded.
- Windows: never os.replace onto an existing file another request may open (delete-pending → PermissionError); use rename-no-clobber.
- Env template is `env.example` (no dot): a permission rule blocks Claude from `.env*` files. Copy it to `.env`.
- REST API in the product; MCP only inside Claude Code for dev/testing (base64, 25 MB, LLM round trip).
- Aletheia returns per-segment scores (4 s windows, 2 s step) in ONE call; overall verdict missed a spliced fake, segments caught it. Never window client-side.
- Partly-fake rule: seconds covered by >=2 overlapping fake windows.
- Pillow can't shape Kannada/Hindi (no raqm): render cards as HTML via Playwright.
- Whisper: English transcripts only; Kannada output is garbage.
- Telegram groups: disable privacy mode AND re-add bot; 20 MB download cap.
- Aletheia limits per docs: <=300 s, >=2 s speech (422 not charged), 2 credits/s, min 20.
- PWA share target: Android Chrome only, installed + HTTPS on a STABLE origin (URL change breaks it).
- OGG/Opus accepted directly; ffmpeg only to strip video/normalise.
- Only clone voices with the owner's consent (own/teammate); no cloning of public figures.

## Topics
- `PLAN.md` (root): the build plan with test evidence; `.project-memory/PLAN.md` tracks step status. Read before starting or finishing a step.
- `research/README.md`: what each spike tests and how to rerun.
- `history/`: what happened and why, one file per day; `history/SUMMARY.md` is one line per month. Search it, don't read it all (see RULES.md).
