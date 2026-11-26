# Plan: Build "Check Before Share" (Track 4) — status tracker
Created 2026-11-24 · Updated 2026-11-26

Full plan, scoring, evidence, contract and lane details: `PLAN.md` (project root) §5. Spikes: `research/`.
This file only tracks step status. Lanes ended 2026-11-25: all changes on the Windows laptop, the Fedora laptop is the server; `testing` branch → `master` when it works.

## Steps
- [x] 0. Research + smoke tests; write `PLAN.md`; split into two lanes
- [ ] Day 0 — A: D1 key · D2 ngrok static domain ✅ · D3 install stack ✅ · D4 Android share check ✅ | B: D1 key ✅ · D2 BotFather ✅ · D3 accuracy test ✅ (real 12/12, clones 6/6, splices 6/6) · D4 fonts ✅ + subreddit rules | both: D5 MCP in Claude Code
- [x] K2–K3. `CONTRACT.md`, `CLAUDE.md`, mock `check()` + fixtures + tests (base commit, 2026-11-25)
- [x] K1. Pushed to GitHub (master); `lane-a` and `lane-b` branches pushed (2026-11-25)
- [x] Phase 1 — A1 normalise + REST client · A2 verdict bands + tests | B1 bot on mock · B2 i18n en/hi/kn (native review pending)
- [x] Sync 1 (MVP): merged on master; spliced clip → 🟠 10–14 s from the real API in the group (2026-11-25)
- [x] Phase 2 — A3 SQLite + fingerprint cache · A4 FastAPI + result page | B3 card (Playwright) · B4 cache-hit wording
- [x] Sync 2: reply + card + live `/r/<id>` timeline over https, 👍 forwarded (demo laptop, real API, 2026-11-25)
- [ ] Phase 3 — [x] A5 PWA (Android install + share passed 2026-11-25) · [x] U2 "hear the fake part": voice note of the flagged seconds + card line (live-tested) · [x] U3 AI-clip radar /radar (live-tested: 7x in 2 chats) · [ ] A6 transcript (stretch, cut) · [x] A7 hardening | [x] B5 README (Sync 2 screenshot + links still to add) · [ ] B6 Reddit draft + backup video · [ ] B7 demo script
- [x] C. Repeat-clip cache hardening (2026-11-25/26, server-tested, in master dec4bbd): decoded-audio layer (other formats) · fpcalc on both laptops · layer 5 speed/tape/pitch copies (9/9) · false-match test (612 pairs, 0 hits) · fingerprint diff (edits ≥ ~2 s never reuse a verdict; 4/4 on the server) · diff feeds the verdict (`apply_edits`). Known limits in README: edits ≤ ~1 s, tuned on 3 male speakers. Possible follow-ups: check only the changed seconds, English transcript veto, big synthetic test set
- [x] L. Live listen (judge's round-1 question; Aletheia live stream `wss://platform.detectif.ai/v1/stream`), on `testing`:
  - [x] L0. Preflight (done as the phone test instead: speaker path gives real-speech false alarms at 0.65-0.85 → live score floor 0.9; `research/live-listen.md`)
  - [x] L1. `app/core/live.py`: relay browser PCM 16 kHz frames → Aletheia stream (API key server-side, never in a URL), pass messages back, write the audio to WAV; cap LIVE_MAX_SECONDS; mock stream when MOCK_ALETHEIA (0 credits); tests
  - [x] L2. `GET /live` page + `WS /ws/live` in `app/api.py`: mic → AudioWorklet → 16 kHz Int16 → 100 ms frames; consent line before Start; live 🟢/🟡/🔴 + seconds checked; en/hi/kn texts
  - [x] L3. On stop: final result (`completed.results.deepfake`: segments) → `verdict.decide` → stored as a check (channel "live", never on the radar) → link to `/r/<id>` (timeline, hear the fake part, 👍/👎)
  - [x] L4. Docs: README (how it works, cost, limits: speakerphone only, consent), CONTRACT, engine diagram; landing-page link
  - [x] L5. Server + phone tests on the real stream (2026-11-26): 5 real-voice calls (en/hi/kn) → 4 no_signs + 1 unclear, 0 red; clone caught; sustained rule `verdict.decide_live`; merged to master
- [x] E. Credit efficiency (user goal, 2026-11-26; done: edited copies pay only new seconds (63 vs 198 credits), edge-silence trim (2 s grid), radar counts edit savings, 476 trial credits; early stop + pause cutting not built (quality); automated server test PASSED 2026-11-26 on Windows (594 trial credits); manual Telegram + WhatsApp tests passed, merged 2026-11-26): E1 safe, 0 credits: cache hit-rate report · trim lead/trail silence · skip no-speech uploads · live auto-stop/reminder | E2 risky, budget <=1-2k credits (keep >=500-800 for demo): A re-check only edited seconds (~200) · B cut inner pauses + remap (~400-500) · C long clips in parts (~150); pass = 0 new false alarms, fakes still caught (region +-1 s), >=15% saved; failures written up in research/
- [ ] D. Final-round docs (user, 2026-11-26; Reddit post no longer required): [x] D1 PPT on the technical stack (submission/Check Before Share — Tech Stack.pptx) · [x] D2 PDF explaining the whole project + judging Q&A (submission/check-before-share-explainer.pdf) · [ ] D3 B7 demo script (`submission/demo.md`). See HANDOFF.md
- [ ] Sync 3 freeze → F1 rehearse ×3 · F2 final video + Reddit post live (required) · F3 tag repo + Google form
- [ ] V. Demo video (1:55, friend's SHOTLIST.md on demo laptop `data/demo-video/`): title cards ✅ (friend) · hero clip = Deepesh's spliced notice (`~/Downloads/demo-clips/AUD-20261125-WA0011.ogg`, fake 10.05–13.77 s) · fresh DB + radar recording (friend) · phone clips 3 hero, 4 timeline tap, 5 spread to 2nd/3rd chat, 6 WhatsApp share, 7 honest results (Deepesh) · rough cut + narration

## Constraints and decisions
- See root `PLAN.md` §2 and "Constraints and decisions". REST API in product, MCP for dev only.

## Open questions
- Build hours on Day 1; who has the Android phone; hackathon credit balance; Kannada false-alarm rate; product name.
