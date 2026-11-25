# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Base scaffold in `app/` (mock `check()` works; lane modules are stubs). Python 3.11, FastAPI, python-telegram-bot. Tests: `python -m pytest -q`.

## Current work
- Goal: build Track 4 "Check Before Share" (ideas 1+3+4+6+7, Aletheia only) at the hackathon; team of 2, each with Claude Code.
- Plan: `PLAN.md` §5 (Lane A engine+web, Lane B bot+card+story; interface in `CONTRACT.md`, session rules in `CLAUDE.md`); status in `.project-memory/PLAN.md`.
- Done: research + smoke tests; base scaffold committed (contract, mock check() on real fixtures, stubs, 9 contract tests pass, 9 verdict tests skip until A2).
- In progress: none.
- Next: 1) K1 push to GitHub + add teammate 2) each person: `lane-a`/`lane-b` branch, `.env` from `env.example` 3) Day 0 per lane, then A1 / B1.
- Blockers / open questions: build hours; who has the Android phone; credit balance; Kannada false-alarm rate.
- Updated: 2026-11-25, Claude

## Rules & gotchas
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
