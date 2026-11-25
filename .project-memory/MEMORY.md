# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Default language English (`DEFAULT_LANG`). Python 3.11, FastAPI, python-telegram-bot. Tests: `.venv/Scripts/python -m pytest -q` (venv on this PC).

## Current work
- Goal: build Track 4 "Check Before Share" (ideas 1+3+4+6+7, Aletheia only) at the hackathon; team of 2, each with Claude Code.
- Setup (since 2026-11-25): no more Lane A/B. All changes on this Windows laptop; the Fedora laptop is the server (bot + API). Commit + push to branch `testing`; merge into `master` only when it works. Plan: `PLAN.md`; status in `.project-memory/PLAN.md`.
- Done: research (0/12 real false alarms); bot, card, web, PWA share; Sync 1+2; hear-the-fake-part; AI-clip radar. Step L live listen DONE 2026-11-26 (/live, Aletheia live stream, sustained rule; `research/live-listen.md`). Step C cache hardening DONE 2026-11-26 (formats, speed/pitch copies, fingerprint diff + verdict; `research/fp_diff.md`).
- In progress: demo video (PLAN.md step V): friend's kit + title cards done on demo laptop; Lane B phone clips 3-7 next; files in ~/Downloads/demo-clips (WA0011 spliced hero, WA0012 real, WA0013 clone).
- Next: 1) user confirms own voice OK in video + sends hero-* files to friend 2) phone setup + 2 extra Telegram groups 3) 'start recording session' (fresh DB) -> clips 3-7 -> 'done'; rough cut 4) B6 Reddit + B7 demo script last.
- Blockers / open questions: build hours; who reads Kannada best (native review of new hi/kn lines too); asked organizers for ~10k extra credits, awaiting reply; old pre-layer-5 speed-copy checks (ytu2eA edQR-A vX-ksg jB7LTA ZOD39w 5kAVrg) still in the real DB, delete? (user's call).
- Updated: 2026-11-26, Claude (Windows dev laptop)

## Rules & gotchas
- Facts in the root `CLAUDE.md` (segments, Pillow, Whisper, Telegram, consent) aren't repeated here.
- Before cache work read `cache.md`; before verdict/API/live work `aletheia.md`; before running or deploying `deploy.md`.
- Merge `testing` → `master` only after a server test passes; give the Fedora laptop a prompt that asks for a SHORT report.

## Topics
- `submission/engine-flow.html`: engine workflow diagram (published artifact https://claude.ai/artifact/6rn99xKVfsqftwRxKNbMox); update it if check() flow changes.
- `.project-memory/PLAN.md` (4 KB): step status; read before starting or finishing a step. Root `PLAN.md` (29 KB, evidence): grep it for the step, don't read it whole.
- `research/README.md`: what each spike tests and how to rerun.
- `cache.md`, `aletheia.md`, `deploy.md`: topic files (read when the task touches them).
- `history/`: what happened and why, one file per day; `history/SUMMARY.md` is one line per month. Search it, don't read it all (see RULES.md).
