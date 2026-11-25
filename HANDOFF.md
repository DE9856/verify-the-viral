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
1. **Ask the user** the open questions below (Reddit post status first: no Reddit link, no shortlist).
2. **Efficiency fixes the user was deciding on** (proposed, not started):
   live-call WAV → Opus after Stop (~16× smaller, `app/core/live.py`), and a cleanup that deletes
   stored audio older than N days but keeps results. Later: cut long silences before upload to save
   credits (needs timeline remapping + a test).
3. **Step V, demo video** (2 min): friend's shot list on the old demo laptop `data/demo-video/`
   (title cards done); hero = the spliced notice `~/Downloads/demo-clips/AUD-20261125-WA0011.ogg`
   (fake 10.05–13.77 s), real = WA0012, clone = WA0013. Phone clips 3–7 still to record; add a
   live-listen segment (real voice 🟢 → clone 🔴 → Stop → timeline). Rough cut + narration.
4. **B6 Reddit post** (required, one of r/cybersecurity, r/fintech, r/speechtech, r/developersIndia;
   honest, with a demo video/screenshots) and **B7 demo script** (`submission/demo.md`).
5. **Sync 3 / final**: rehearse ×3, final video, tag the repo, Google form with the Reddit link.

## Waiting on the user
- Was the Reddit post (B6) made for round 1? If yes, tick B6 in `.project-memory/PLAN.md`.
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
