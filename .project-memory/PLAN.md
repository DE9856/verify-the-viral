# Plan: Build "Check Before Share" (Track 4) — status tracker
Created 2026-11-24 · Updated 2026-11-25

Full plan, scoring, evidence, contract and lane details: `PLAN.md` (project root) §5. Spikes: `research/`.
This file only tracks step status. Team of 2: Lane A = engine + web, Lane B = bot + card + story.

## Steps
- [x] 0. Research + smoke tests; write `PLAN.md`; split into two lanes
- [ ] Day 0 — A: D1 key · D2 ngrok static domain · D3 install stack · D4 Android share check | B: D1 key · D2 BotFather (privacy off) · D3 real voice-note/clone accuracy test · D4 fonts + subreddit rules | both: D5 MCP in Claude Code
- [x] K2–K3. `CONTRACT.md`, `CLAUDE.md`, mock `check()` + fixtures + tests (base commit, 2026-11-25)
- [ ] K1. Push to GitHub, add teammate, create `lane-a` / `lane-b` branches
- [ ] Phase 1 — A1 normalise + REST client · A2 verdict bands + tests | B1 bot on mock ✅ (2026-11-25) · B2 i18n en/hi/kn
- [ ] Sync 1 (MVP): spliced clip → 🟠 10–14 s reply from the real API
- [ ] Phase 2 — A3 SQLite + fingerprint cache · A4 FastAPI + result page | B3 card (Playwright) · B4 cache-hit wording
- [ ] Sync 2: reply + card + live `/r/<id>` timeline
- [ ] Phase 3 — A5 PWA (cut first) · A6 transcript (stretch) · A7 hardening | B5 README · B6 Reddit draft + backup video · B7 demo script
- [ ] Sync 3 freeze → F1 rehearse ×3 · F2 final video + Reddit post live (required) · F3 tag repo + Google form

## Constraints and decisions
- See root `PLAN.md` §2 and "Constraints and decisions". REST API in product, MCP for dev only.

## Open questions
- Build hours on Day 1; who has the Android phone; hackathon credit balance; Kannada false-alarm rate; product name.
