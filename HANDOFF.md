# Handoff — pick up here (written 2026-11-26)

For the next Claude Code session on a new dev laptop. Read this file, then `.project-memory/MEMORY.md`
(loaded automatically) and `.project-memory/PLAN.md` (step status). Ask the user only what is under
**Waiting on the user**.

## Where things stand
- Product: **Check Before Share**, CMRIT × DetectifAI hackathon, Track 4 "Verify the Viral" (Aletheia only).
  Telegram bot + web app/PWA + live listen. Round 1 is done; the final round uses the same scoring
  (30 use of Aletheia · 30 usefulness · 25 works live · 15 honest results). Guide: `CMRIT_DetectifAI_Hackathon_Guide.pdf`
  (not in git; the user has it in Downloads).
- Code: `master` = `testing` = the latest commit, all tests pass (`python -m pytest -q`, 140).
- Done and server-tested: bot, card, result page, PWA share, AI-clip radar, hear-the-fake-part;
  **step C** cache hardening (other formats, speed/pitch copies, fingerprint diff, diff feeds the verdict);
  **step L** live listen (`/live`, Aletheia live stream, sustained-evidence rule). Evidence in `research/*.md`.
- Server: the **Fedora laptop** runs ngrok + API + bot on the real `data/app.db`. It was on `testing`
  `d6b9ab0`; it should `git checkout master && git pull` (only docs changed since, no restart needed).

## Workflow (agreed with the user)
- All code changes on the dev laptop (this was the Windows laptop until now). No lanes any more.
- Commit and push to **`testing`**; merge `testing` → `master` (fast-forward) only after a server test passes.
- The user asks Claude to commit and push. Commit messages end with the Co-Authored-By line from the reminder.
- Server tests: write a prompt for the Claude Code on the Fedora laptop; ask for a SHORT report
  (verdict + anomalies; tables only on failure). Judge cache tests by the `via=` log line, not credits
  (same bytes within 24 h are free). Clean tests use `DB_PATH=data/<name>.db` in the shell.
- Develop with `MOCK_ALETHEIA` set (0 credits). Credits are tight: say the cost before any real-API test.

## Setting up the new laptop
1. `git clone` the repo, `git checkout testing`.
2. Python 3.11 venv; `pip install -r requirements.txt` (includes `websockets` for live listen);
   `playwright install chromium`.
3. Chromaprint `fpcalc`: Windows → download 1.5.1 from github.com/acoustid/chromaprint/releases into `bin/`;
   Linux → `sudo dnf install chromaprint-tools` (or apt `libchromaprint-tools`). `/health` warns if missing.
4. `.env` from `env.example` (keys: `DETECTIF_API_KEY`, `TELEGRAM_BOT_TOKEN`; the user has them).
   Claude can't read `.env*` (permission rule); never print secrets.
5. Private audio (our own consented voices, deliberately NOT in git): unzip `handoff-private-audio.zip`
   (the user carries it from the old laptop's Downloads): `repo/research/real-audio/` → the repo's
   `research/real-audio/`; `Downloads/*` → `~/Downloads/` (demo-clips, live-test, edit-test, speed-test, speed-test-2).
6. Check: `python -m pytest -q` → 140 pass (with and without `MOCK_ALETHEIA`).

## Next (in order)
1. **Ask the user** the open questions below.
2. **Efficiency fixes the user was deciding on** (proposed, not started):
   live-call WAV → Opus after Stop (~16× smaller, `app/core/live.py`), and a cleanup that deletes
   stored audio older than N days but keeps results. Later: cut long silences before upload to save
   credits (needs timeline remapping + a test).
3. **Step V, demo video** (2 min): friend's shot list on the old demo laptop `data/demo-video/`
   (title cards done); hero = the spliced notice `~/Downloads/demo-clips/AUD-20261125-WA0011.ogg`
   (fake 10.05–13.77 s), real = WA0012, clone = WA0013. Phone clips 3–7 still to record; add a
   live-listen segment (real voice 🟢 → clone 🔴 → Stop → timeline). Rough cut + narration.
4. **Final-round deliverables (user, 2026-11-26): the Reddit post is NOT required any more.** Instead:
   - **A presentation (PPT) explaining the technical stack**: architecture (bot / web + PWA / live
     listen → `check()` → cache layers → Aletheia REST + live stream → verdict rules → SQLite →
     card / result page / radar), why each choice (segments not client windowing, HTML→PNG cards for
     Kannada/Hindi, relay for the live stream key, sustained live rule), test evidence with numbers,
     honest limits. Make it with the Artifact tool's slides type (exports .pptx/PDF) or the pptx skill;
     reuse `submission/engine-flow.html` as the architecture slide.
   - **A PDF that explains the whole project properly**: problem, what it does (all entry points),
     how it works end to end, every test and its numbers (`research/real-world.md`, `speed-test.md`,
     `false-match.md`, `fp_diff.md`, `live-listen.md`), limits, privacy/consent, how to run it —
     plus a **judging Q&A section** (questions judges may ask, with short honest answers; starter
     list below). Sources: `README.md`, `CONTRACT.md`, `research/*.md`, `.project-memory/history/`.
   - **B7 demo script** (`submission/demo.md`) for the live demo ("works live in the demo" = 25 points).
5. **Sync 3 / final**: rehearse ×3, final video, tag the repo, submit (repo + 2-min video + README).

### Starter Q&A for the judging round (answers live in the docs; verify numbers before quoting)
- Why Aletheia's segments and not just its verdict? → the overall verdict called our spliced clip real; the 4 s windows caught it (`README.md`).
- How accurate is it on real Indian voices? → 0/12 false alarms on real en/hi/kn voice notes; clones 6/6, splices 6/6 (`research/real-world.md`); small test set, male voices only.
- What if someone forwards the same fake again, re-encoded, sped up or pitch-shifted? → 5 cache layers, 0 credits; 9/9 speed/pitch copies on the server (`research/speed-test.md`).
- Could the cache give a fake the verdict of a real clip? → whole-clip scores average short fakes away; the fingerprint diff refuses any copy with ≥ ~2 s changed (`research/fp_diff.md`, `false-match.md`); ~1 s swaps are the known limit.
- Does it work on live calls? (asked in round 1) → yes, `/live` with Aletheia's live stream through the speaker; phones block call audio; the sustained rule stops speaker false alarms (`research/live-listen.md`).
- What does it cost? → 2 credits/s, min 20; repeats free; live bills speech only.
- Why Telegram and not WhatsApp? → WhatsApp has no bot API for groups; Android share sheet covers WhatsApp users (PWA).
- Kannada/Hindi support? → replies, cards and pages in en/hi/kn; Aletheia works best on English and Hindi (docs).
- Privacy? → clips deleted after checking (bot), chats only as salted hashes for the radar, live checks private, key never in the browser.
- How do you avoid overclaiming? → four honest bands incl. "unclear", "a score is evidence, not proof", 👍/👎 feedback to DetectifAI.
- What would you build next? → check only the changed seconds of an edited copy, English transcript veto, silence trimming for credits, bigger test set.

## Waiting on the user
- Go ahead with the two efficiency fixes (WAV → Opus, audio cleanup)?
- Delete the 6 old pre-layer-5 speed-copy checks from the server DB (ytu2eA edQR-A vX-ksg jB7LTA
  ZOD39w 5kAVrg)? They carry misleading 0.5×/2× results. User's call (command in history 2026-11-25).
- Native-speaker review of the Hindi and Kannada texts added this session (edited copy, unclear-edited,
  speed/pitch copy lines, all `live_*` texts).
- Organizers' reply to the ~10,000-credit request.

## Gotchas worth knowing before touching things
- Topic files: `.project-memory/cache.md` (cache layers), `aletheia.md` (API, live stream, live rule),
  `deploy.md` (server start commands, ngrok/PWA, env).
- Live listen through a speaker can make 2–4 s of real speech "fake" (0.65–0.97, varies per run);
  the live rule needs ≥ 3 overlapping confident windows. Don't add score floors: they overfit.
- Fingerprint whole-clip scores average away short fakes; every fuzzy cache hit must pass `fpdiff`.
- Engine diagram `submission/engine-flow.html` is a published artifact
  (https://claude.ai/artifact/6rn99xKVfsqftwRxKNbMox); republish it when the check() flow changes.
