# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Lane A engine + web (`app/core/*`, `app/api.py`, result page, PWA) and Lane B bot + card + wording (`app/bot.py`, `app/core/card.py`, `app/i18n.json`) merged on master at Sync 1. Default language English (`DEFAULT_LANG`). Python 3.11, FastAPI, python-telegram-bot. Tests: `.venv/Scripts/python -m pytest -q` (venv on this PC).

## Current work
- Goal: build Track 4 "Check Before Share" (ideas 1+3+4+6+7, Aletheia only) at the hackathon; team of 2, each with Claude Code.
- Setup (since 2026-11-25): no more Lane A/B. All changes on this Windows laptop; the Fedora laptop is the server (bot + API). Commit + push to branch `testing`; merge into `master` only when it works. Plan: `PLAN.md`; status in `.project-memory/PLAN.md`.
- Done: research; real-voice test 0/12 false alarms (`research/real-world.md`); Lane A A1-A5+A7; Lane B B1-B5; Sync 1 + **Sync 2 passed** (demo laptop, real API: reply + card + https /r/<id> red 10-14 s, 👍 forwarded); A5 Android install + share passed; U2 'hear the fake part' + U3 AI-clip radar (/radar) live.
- In progress: demo video (PLAN.md step V): friend's kit + title cards done on demo laptop; Lane B phone clips 3-7 next; files in ~/Downloads/demo-clips (WA0011 spliced hero, WA0012 real, WA0013 clone).
- Next: 1) user confirms own voice OK in video + sends hero-* files to friend 2) phone setup + 2 extra Telegram groups 3) 'start recording session' (fresh DB) -> clips 3-7 -> 'done'; rough cut 4) B6 Reddit + B7 demo script last.
- Blockers / open questions: build hours; Kannada: 0 false alarms, clone + splice caught; who reads Kannada best; asked organizers for ~10k extra credits (efficiency experiments), awaiting reply.
- Updated: 2026-11-25, Claude (Windows dev laptop)

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
- PWA share target: Android Chrome only, installed + HTTPS on a STABLE origin (URL change breaks it). ngrok free shows a one-time "Visit Site" page in browsers (cookie abuse_interstitial); cookie-less fetches like the manifest get that page, so manifest links need crossorigin="use-credentials". Fallback: Tailscale Funnel. Start (repo root): `ngrok http --url=spirits-bauble-astronomy.ngrok-free.dev 8000`, `uvicorn app.api:app --host 127.0.0.1 --port 8000`, `python -m app.bot`; PUBLIC_BASE_URL needs `https://`.
- OGG/Opus accepted directly; ffmpeg only to strip video/normalise.
- Only clone voices with the owner's consent (own/teammate); no cloning of public figures.

## Topics
- `submission/engine-flow.html`: engine workflow diagram (published artifact https://claude.ai/artifact/6rn99xKVfsqftwRxKNbMox); update it if check() flow changes.
- `PLAN.md` (root): the build plan with test evidence; `.project-memory/PLAN.md` tracks step status. Read before starting or finishing a step.
- `research/README.md`: what each spike tests and how to rerun.
- `history/`: what happened and why, one file per day; `history/SUMMARY.md` is one line per month. Search it, don't read it all (see RULES.md).
