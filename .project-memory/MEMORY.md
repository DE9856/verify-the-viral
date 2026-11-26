# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Default language English (`DEFAULT_LANG`). Python 3.11, FastAPI, python-telegram-bot. Tests: `.venv/Scripts/python -m pytest -q` (venv on this PC).

## Current work
- **New laptop? Read `HANDOFF.md` first** (setup, private-audio zip, workflow, what's next).
- Goal: Track 4 "Check Before Share" (Aletheia only), hackathon final round; team of 2, each with Claude Code.
- Setup: one laptop now (Windows = dev + server: API + bot + ngrok, see deploy.md); push `testing` → merge to `master` after a server test. Plan status: `.project-memory/PLAN.md`.
- Done: research (0/12 real false alarms); bot, card, web, PWA share; Sync 1+2; hear-the-fake-part; AI-clip radar; step C cache hardening; step L live listen. step E credit efficiency. master = testing, 150 tests pass.
- In progress: nothing open; efficiency safety fixes merged to master (152 pass): cut excerpt, clean-diff rule (stray), regions kept outside changes, -45 dBFS trim floor; 84 vs 198 credits; PDF + PPT updated.
- Next: 1) rehearse submission/demo.md (backup recording, separate DB) 2) step V video 3) Sync 3 (rehearse, tag, submit).
- Blockers / open questions: known minor (user: fine, not fixing): edit-excerpt regions ~0.67 s late, no bot error handler, one lost 👍; current credit balance (check GET /v1/credits, free); bot checks every group voice note: keep or forwarded-only + /check?; delete 6 old speed-copy checks?; hi/kn native review; organizers' ~10k credits reply.
- Updated: 2026-11-26, Claude (Windows: pulled 7c4e476, server restarted on it; teammate PPT is the deck)

## Rules & gotchas
- Edited copies take the cheap path (excerpt/free) only on a clean diff: typical >= 0.90 and fpdiff `stray` <= 0.3 s; else whole clip.
- Sent copy may differ from the stored one: edge silence trimmed (normalize.send_path/offset); Aletheia times are shifted back. Never cut a clip's start by a non-multiple of 2 s (moves the window grid).
- Facts in the root `CLAUDE.md` (segments, Pillow, Whisper, Telegram, consent) aren't repeated here.
- Before cache work read `cache.md`; before verdict/API/live work `aletheia.md`; before running or deploying `deploy.md`.
- Merge `testing` → `master` only after a server test passes; give the Fedora laptop a prompt that asks for a SHORT report.

## Topics
- `submission/engine-flow.html`: engine workflow diagram (published artifact https://claude.ai/artifact/6rn99xKVfsqftwRxKNbMox); update it if check() flow changes.
- Tech-stack deck (D1): use `submission/Check Before Share — Tech Stack.pptx` (user decision); the Artifact deck 9kewhg9HuMFwEyuiJqnJhs is unused (old numbers).
- `.project-memory/PLAN.md` (4 KB): step status; read before starting or finishing a step. Root `PLAN.md` (29 KB, evidence): grep it for the step, don't read it whole.
- `research/README.md`: what each spike tests and how to rerun.
- `cache.md`, `aletheia.md`, `deploy.md`: topic files (read when the task touches them).
- `HANDOFF.md` (repo root): pick-up guide for a new laptop/session.
- `history/`: what happened and why, one file per day; `history/SUMMARY.md` is one line per month. Search it, don't read it all (see RULES.md).
