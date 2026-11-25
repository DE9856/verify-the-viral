# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Default language English (`DEFAULT_LANG`). Python 3.11, FastAPI, python-telegram-bot. Tests: `.venv/Scripts/python -m pytest -q` (venv on this PC).

## Current work
- **New laptop? Read `HANDOFF.md` first** (setup, private-audio zip, workflow, what's next).
- Goal: Track 4 "Check Before Share" (Aletheia only), hackathon final round; team of 2, each with Claude Code.
- Setup: dev laptop makes all changes → push `testing` → merge to `master` after a server test; Fedora laptop = server (bot + API + ngrok). Plan status: `.project-memory/PLAN.md`.
- Done: research (0/12 real false alarms); bot, card, web, PWA share; Sync 1+2; hear-the-fake-part; AI-clip radar; step C cache hardening; step L live listen. master = testing, 140 tests pass.
- In progress: nothing uncommitted. Demo video (step V): title cards done; phone clips 3-7 + live-listen segment to record.
- Next: 1) ask the user the open questions 2) efficiency fixes if approved (live WAV -> Opus, audio cleanup) 3) step V video 4) B6 Reddit + B7 demo script 5) Sync 3 (rehearse, tag, Google form).
- Blockers / open questions: Reddit post (B6) made?; approve efficiency fixes?; delete 6 old speed-copy checks on the server?; native review of new hi/kn texts; organizers' reply on ~10k credits.
- Updated: 2026-11-26, Claude (Windows dev laptop, handoff)

## Rules & gotchas
- Facts in the root `CLAUDE.md` (segments, Pillow, Whisper, Telegram, consent) aren't repeated here.
- Before cache work read `cache.md`; before verdict/API/live work `aletheia.md`; before running or deploying `deploy.md`.
- Merge `testing` → `master` only after a server test passes; give the Fedora laptop a prompt that asks for a SHORT report.

## Topics
- `submission/engine-flow.html`: engine workflow diagram (published artifact https://claude.ai/artifact/6rn99xKVfsqftwRxKNbMox); update it if check() flow changes.
- `.project-memory/PLAN.md` (4 KB): step status; read before starting or finishing a step. Root `PLAN.md` (29 KB, evidence): grep it for the step, don't read it whole.
- `research/README.md`: what each spike tests and how to rerun.
- `cache.md`, `aletheia.md`, `deploy.md`: topic files (read when the task touches them).
- `HANDOFF.md` (repo root): pick-up guide for a new laptop/session.
- `history/`: what happened and why, one file per day; `history/SUMMARY.md` is one line per month. Search it, don't read it all (see RULES.md).
