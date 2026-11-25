# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Lane A engine + web (`app/core/*`, `app/api.py`, result page, PWA) and Lane B bot + card + wording (`app/bot.py`, `app/core/card.py`, `app/i18n.json`) merged on master at Sync 1. Python 3.11, FastAPI, python-telegram-bot. Tests: `.venv/Scripts/python -m pytest -q` (venv on this PC).

## Current work
- Goal: build Track 4 "Check Before Share" (ideas 1+3+4+6+7, Aletheia only) at the hackathon; team of 2, each with Claude Code.
- Plan: `PLAN.md` §5; status in `.project-memory/PLAN.md`. This PC = **Lane B** (bot+card+story); teammate = Lane A.
- Done: research; real-voice test 0/12 false alarms (`research/real-world.md`); Lane A A1-A5+A7 (see `PLAN.md` §5.7); Lane B B1-B4 (bot on Telegram, /lang, card, 👍/👎); Sync 1 merge on master.
- In progress: Sync 1 done-when: real API test (spliced clip -> 🟠 10-14 s in group); needs `MOCK_ALETHEIA=` empty in `.env`. README draft (B5) stashed on lane-b (`git stash list`), awaiting user review. Clone rerun with `clone-handoff-v2.zip` on GPU laptop.
- Next: 1) real-API Sync 1 test 2) Sync 2: Lane A server + ngrok static domain, PUBLIC_BASE_URL https -> timeline button + cache live 3) B6 Reddit draft + B7 demo script 4) clone results -> README.
- Blockers / open questions: build hours; who has the Android phone; Kannada false alarms: 0/4 on our voices (Hindi runs hottest); who reads Kannada best.
- Updated: 2026-11-25, Claude (Lane B, at Sync 1)

## Rules & gotchas
- Voice notes go to Aletheia unchanged (passthrough); only odd formats are transcoded. `fpcalc.exe` in `bin/` (gitignored); without it only exact cache tiers work.
- Windows: never os.replace onto a file another request may open (PermissionError); use rename-no-clobber.
- Env template is `env.example` (no dot): a permission rule blocks Claude from `.env*` files. Copy it to `.env`.
- REST API in the product; MCP only inside Claude Code for dev/testing (base64, 25 MB, LLM round trip).
- Aletheia returns per-segment scores (4 s windows, 2 s step) in ONE call; overall verdict missed a spliced fake, segments caught it. Never window client-side.
- Partly-fake rule: seconds covered by >=2 overlapping fake windows.
- Segment `verdict` uses its own threshold (0.883 came back real): read the field, never score>0.62.
- Pillow can't shape Kannada/Hindi (no raqm): render cards as HTML via Playwright.
- Whisper: English transcripts only; Kannada output is garbage.
- Telegram groups: disable privacy mode AND re-add bot; 20 MB download cap. Bot = @verifytheviralbot; httpx logger must stay at WARNING (URLs carry the token).
- Aletheia limits per docs: <=300 s, >=2 s speech (422 not charged), 2 credits/s, min 20.
- PWA share target: Android Chrome only, installed + HTTPS on a STABLE origin (URL change breaks it).
- OGG/Opus accepted directly; ffmpeg only to strip video/normalise.
- Only clone voices with the owner's consent (own/teammate); no cloning of public figures.

## Topics
- `PLAN.md` (root): the build plan with test evidence; `.project-memory/PLAN.md` tracks step status. Read before starting or finishing a step.
- `research/README.md`: what each spike tests and how to rerun.
- `history/`: what happened and why, one file per day; `history/SUMMARY.md` is one line per month. Search it, don't read it all (see RULES.md).
