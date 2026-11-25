# Project memory
Shared memory for this folder. Before editing anything in `.project-memory/`, read `.project-memory/RULES.md`.
Asked about the project's past? If the answer isn't below or in a topic file, search `.project-memory/history/` for the key words before saying it isn't recorded.

## Overview
Team entry for the CMRIT × DetectifAI hackathon (2 days, teams of 2–3). Must use DetectifAI's Aletheia (deepfake detection) and/or Eidos (speaker verification) via the API or MCP at platform.detectif.ai. Brief: `CMRIT_DetectifAI_Hackathon_Guide.pdf`. Plan: `PLAN.md`; research spikes + test audio: `research/`. Base scaffold in `app/` (mock `check()` works; lane modules are stubs). Python 3.11, FastAPI, python-telegram-bot. Tests: `.venv/Scripts/python -m pytest -q` (venv on this PC).

## Current work
- Goal: build Track 4 "Check Before Share" (ideas 1+3+4+6+7, Aletheia only) at the hackathon; team of 2, each with Claude Code.
- Plan: `PLAN.md` §5; status in `.project-memory/PLAN.md`. This PC = **Lane B** (bot+card+story); teammate = Lane A.
- Done: research + scaffold; repo on GitHub (origin DE9856/verify-the-viral); Lane B setup here (.venv, deps, Chromium, branch `lane-b`); D3 scripts in `research/script.md`.
- In progress: Lane A done on origin/lane-a (6056d90); trial merge with lane-b = 98 pass (local branch trial-merge). Next: Lane B asks from NOTES-FOR-B ("checking..." msg, card colours #e5484d/#f5a524/#2f9e66), then Sync 1 merge to master (needs both OK) + real-API spliced test. README draft uncommitted. D3: real clips done (0/12 false alarms, `research/real-world.md`); still need clone_en + fake_sentence_en (+ hi/kn clones) on the GPU laptop: Chatterbox for en, IndicF5 for hi/kn; handoff `~/Downloads/clone-handoff.zip` sent to GPU laptop, expect back `clones_return.zip` (6 wavs: clone_/fake_sentence_ x en,hi,kn) → build spliced_xx, add to FILES in `real_world_test.py`, run, then spliced_en; rerun `research/spikes/real_world_test.py --run`. Credits left 4266.
- Next: 1) user tests /lang in group; reviewer fills `research/i18n-review.md`, Claude applies fixes to `app/i18n.json`, commit+push 2) when `clones_return.zip` arrives: build spliced_xx, run `research/spikes/real_world_test.py --run`, finish `research/real-world.md` 4) D4: Noto fonts + subreddit rules.
- Blockers / open questions: build hours; who has the Android phone; Kannada false alarms: 0/4 on our voices (Hindi runs hottest); who reads Kannada best.
- Updated: 2026-11-25, Claude

## Rules & gotchas
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
