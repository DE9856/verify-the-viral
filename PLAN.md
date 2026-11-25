# Plan: "Check Before Share" — Track 4 (Verify the Viral) build plan
Created 2026-11-24 · Updated 2026-11-25 · Working name, rename freely

**One-liner:** a Telegram group guardian + Android share-sheet app that checks any voice note or video
with DetectifAI's Aletheia, shows *which seconds* sound AI-generated, and hands back a forwardable
verdict card — so the fact-check travels instead of the fake.

Scope agreed with the team: ideas **1** (spliced-fake timeline), **3** (Telegram group bot),
**4** (PWA share target, our WhatsApp route), **6** (verdict card), **7** (fingerprint cache).
Aletheia only, no Eidos.

---

## 1. What we tested (smoke runs, 2026-11-24)

Everything below was actually run. Scripts, raw JSON results and screenshots are in `research/`.

### 1a. Aletheia itself (6 checks on the free MCP trial, no API key)

Test audio: public-domain human speech (Open Speech Repository, 8 kHz phone quality) and neural
TTS "fakes" (Microsoft Edge voices — generic voices, nobody cloned). Spliced clip = real speech
0–10 s + one fake sentence at **10.0–14.8 s** + real speech.

| Clip | Truth | Overall verdict | Segments (4 s windows, 2 s step) |
|---|---|---|---|
| Real human, 8 kHz | real | ✅ real (0.07) | all real, max 0.31 |
| TTS English / Hindi / **Kannada** | fake | ✅ fake (≥ 0.999) | all fake |
| Spliced (real + 1 fake sentence) | mixed | ❌ **real (0.28)** | ✅ 8–16 s fake (0.98–1.00) |
| Same, re-encoded Opus 16 kbps (WhatsApp-like) | mixed | ❌ real (0.25) | ✅ 8–16 s fake |

- Latency ≈ 0.4 s per check (model `aletheia 2026.10`).
- **The headline finding for our pitch:** the overall verdict lets a spliced fake through; the
  segment data catches it, even after WhatsApp-grade compression. Idea 1 is the product, not a
  stretch goal.
- **"Core region" rule** (seconds covered by ≥ 2 overlapping fake windows) localised the fake to
  **10–14 s** vs ground truth 10.0–14.8 s. "Any fake window" gives a sloppier 8–16 s.
- Caveat, honestly: n = 1 per row, and Edge TTS is an easy fake. Real voice clones and real
  Kannada voice notes are untested → Day-0 step D4.

### 1b. Facts from the docs that change the plan (platform.detectif.ai/docs, read 2026-11-24)
- One call to `POST /v1/deepfake/detect` already returns `segments[]` (4 s windows, 2 s step).
  **No client-side windowing** — that would cost ~5× (20-credit minimum per call).
- Limits: up to **300 s** and 100 MB per file (the PDF said 120 s; docs are newer). Needs ≥ 2 s of
  speech, else `422 insufficient_speech` — **not charged**. ≥ 10 s of speech is far more reliable
  (docs: 4.2 % false alarms on 4 s vs 0.45 % on 10 s).
- Accepts WAV, MP3, FLAC, **OGG/Opus**, WebM, M4A/AAC, AIFF → Telegram/WhatsApp voice notes go in as-is.
- Price: **2 credits / second**, min 20 per check. 30 s clip = 60 credits. New accounts get 5,000
  free credits (≈ 80 checks of 30 s); hackathon credits may differ — check `GET /v1/credits`.
- `Idempotency-Key` header: same key + same request within 24 h returns the stored result, free.
- Docs: "works best on English and Hindi"; phone-quality audio is less reliable.
- MCP trial at `https://platform.detectif.ai/mcp/trial`: 10 free checks per network address.
  **We used 6; 4 remain** for this network.
- MCP trial responses carry `label`/`is_synthetic` but no top-level `verdict` → read
  `verdict` with a fallback to `label`.

### 1c. Everything else we smoke-tested

| Test | Result |
|---|---|
| Fingerprint: SHA-256 of file / of decoded PCM | ❌ breaks on every re-encode (expected) |
| Fingerprint: **Chromaprint `fpcalc`** | ✅ re-encodes (Opus 16k, Opus ×2, MP3 64k, AAC-from-MP4, −6 dB, 1.3 s trim) all ≥ **0.89**; different clips ≤ **0.71** (even one sharing the first 10 s). Threshold **0.80**. 242 ms / 25 s clip |
| Fingerprint: home-made numpy (Philips-style) | ✅ but thinner margin: same ≥ 0.83, different ≤ 0.70. 170 ms |
| Card: Pillow (no libraqm on Windows wheel) | ❌ **Kannada and Hindi render broken** (split conjuncts, misplaced matras) |
| Card: HTML → PNG with Playwright/Chromium | ✅ Kannada + Hindi correct; **25 ms warm**, 1.9 s cold start |
| Timeline: wavesurfer.js 7.8.6 + regions | ✅ playable waveform, red region sits exactly on the fake; ready in 405 ms |
| Timeline: plain per-0.5 s heat strip | ✅ zero deps, coarser; good for the card |
| Transcript: faster-whisper `base`, CPU, English | ✅ 2.2 s for 25 s; word timestamps ∩ core region = **exactly the fake sentence** |
| Transcript: Hindi | ⚠️ `base` outputs Urdu script even when forced; `small` gives Devanagari, ~9 s, some errors |
| Transcript: Kannada | ❌ garbage at every size; `small` hallucinated for 112 s |
| Share-target POST → FastAPI → ffmpeg normalise → fpcalc | ✅ OGG voice note, MP4 video, MP3 all handled, 0.34–0.49 s each |
| Telegram Bot API docs | Confirmed: privacy mode hides group media unless disabled (and bot re-added) or bot is admin; bot downloads capped at **20 MB**; `file_unique_id` is stable across forwards |
| Web Share Target docs | Confirmed: files need `method: POST` + `multipart/form-data` + `files` entry; installed PWA only; experimental (Android Chrome) |
| HTTPS tunnel (cloudflared quick tunnel) | ⏸️ **not run** — publicly exposing a server needs the team's go-ahead. Do it in D3 |

---

## 2. Decisions — approaches compared and scored

Scores are 1–5 per column (5 = best; for Effort and Cost, 5 = cheapest). ✅ = chosen.

### 2.1 How we detect (the core)
| Approach | Accuracy (tested) | Effort | Credits | Demo value | Total /20 |
|---|---|---|---|---|---|
| Overall verdict only | 1 — missed the splice | 5 | 5 | 2 | 13 |
| Client-side 4 s windowing, many calls | 4 | 2 | 1 — ~5× cost | 4 | 11 |
| ✅ **One call + native `segments` + our core-region rule** | 4 — caught + localised splice (real clones untested) | 5 | 5 | 5 | **19** |

### 2.2 API or MCP? → **API in the product, MCP in your Claude Code.** Use both, for different jobs.

MCP is a way for an *AI assistant* to call tools. Our bot and web app aren't AI assistants: they
get a file and need a verdict in under a second, every time. That is what the REST API is for.

| | REST API | MCP |
|---|---|---|
| Who calls it | our code (`httpx.post`) | an AI assistant (Claude Code, Claude, Cursor) |
| Upload | multipart, up to **100 MB** | base64 text (+33 % size), up to **25 MB** |
| Response | full JSON: `verdict`, `segments`, `credits`, `latency_ms` | same data, wrapped as tool output (trial had no top-level `verdict`) |
| Speed / determinism | ~0.4 s, same input → same code path | adds an LLM round trip in the product (seconds, extra cost, an Anthropic key, can vary) |
| Retries | `Idempotency-Key` header | `idempotency_key` argument |
| Price | same credits | same credits |
| Judging ("good use of Aletheia") | counts | counts — the rules accept either |

| Use | Choice | Score /20 |
|---|---|---|
| ✅ Product backend (`core/aletheia.py`) | **REST API** | **19** |
| ✅ Development, in both of your Claude Code sessions | **MCP** — `claude mcp add --transport http detectif https://platform.detectif.ai/mcp --header "Authorization: Bearer $DETECTIF_API_KEY"`; then ask *"check research/test-audio/spliced_en.wav and show which segments are fake"* to sanity-check clips, compare against what our code says, read balances and past operations without writing scripts | 17 |
| Product backend via MCP | ❌ heavier, slower, 25 MB cap, no gain | 8 |

Worth one line in the README and Reddit post: "We used the MCP server in Claude Code to explore
results while building, and the REST API in the product."

### 2.3 "Already checked" cache (idea 7) — use tiers, cheapest first
| Tier | Survives re-encode | Cost | Verdict |
|---|---|---|---|
| ✅ 1. Telegram `file_unique_id` | exact forwards only | free, no decode | use first |
| ✅ 2. **Chromaprint** similarity ≥ 0.80 | yes (≥ 0.89 vs ≤ 0.71 tested) | 0.25 s + `fpcalc` binary | main tier |
| Fallback: numpy Philips hash | yes, thinner margin | no binary | only if `fpcalc` can't ship |
| SHA-256 of file/PCM | no | — | ❌ reject |

Bonus: use SHA-256 of the *normalised* audio as the Idempotency-Key, so retries and identical
re-uploads within 24 h cost 0 credits.

### 2.4 Verdict card (idea 6)
| Approach | Indic text | Speed | Effort | Total /20 |
|---|---|---|---|---|
| ✅ **HTML template → PNG via Playwright** (warm browser) | correct | 25 ms warm | 4 (+150 MB Chromium) | **18** |
| Pillow | ❌ broken | 67 ms | 5 | 6 |
| Pillow + libraqm / SVG + cairo | probably OK | fast | 2 (native DLL pain on Windows) — not tested | 11 |

Same HTML/CSS is reused by the timeline page → one design, two outputs.
Bundle Noto Sans Kannada + Devanagari font files locally (don't depend on venue Wi-Fi for fonts).

### 2.5 Timeline (idea 1)
| Approach | Total /20 |
|---|---|
| ✅ **wavesurfer.js 7.12.12 + regions** (bundled locally) on the result page (click the red region → hear the fake) | **18** |
| ✅ Plain heat strip — inside the card only | 15 |
| Chart.js score line | 10 (less intuitive; not built) |

### 2.6 Transcript highlight (stretch)
✅ faster-whisper `base` on CPU, **English only** (tested: isolates the exact fake sentence).
Hindi/Kannada show time ranges only. Cloud STT (e.g. Sarvam) could cover Kannada but is untested
and needs another key → only if everything else is done.

### 2.7 Stack
| Piece | Choice | Why |
|---|---|---|
| Backend | ✅ **FastAPI + uvicorn** (Python 3.11) | spike worked; same language as the audio tools |
| Bot | ✅ **python-telegram-bot 22.x**, long polling | most docs/examples; polling needs no HTTPS. aiogram 3.34 also installs fine — fallback |
| Audio | ffmpeg (`imageio-ffmpeg` bundles it, no admin install) | tested |
| Store | SQLite (one file) | zero setup |
| Processes | `bot.py` and `api.py` as **two processes** sharing a `core/` package + the SQLite file | avoids mixing two async loops; either can crash and restart alone |

### 2.8 HTTPS for the PWA (not yet tested — needs the team's go-ahead)
**An installed PWA is tied to its origin.** If the URL changes, the share target breaks and you
must reinstall. So we need a **stable URL**:
| Option | Stable URL | Setup | Pick |
|---|---|---|---|
| ✅ **ngrok free static domain** | yes | account + 1 command | first choice |
| Deploy (Render/Railway/Fly with Docker: ffmpeg + fpcalc + Chromium) | yes | 1–2 h, cold starts | if a server is wanted |
| cloudflared quick tunnel | **no** — new URL each restart | no account | fallback only |

### 2.9 WhatsApp route
✅ PWA share target (team's choice; Android only). Fallback if it misbehaves on Day 0:
Twilio WhatsApp sandbox (1-to-1 forward to a bot number, works on iPhone, untested).

---

## 3. Verdict logic (honest by design — judging gives 15 % for clear, honest results)

Inputs: overall `verdict`, `segments`, `scored_seconds`.

| Band | Rule | User sees (+ next step) |
|---|---|---|
| 🔴 Likely AI-generated | overall `fake` | "This voice is likely AI-generated (score 0.97). Don't forward. Check the official source." |
| 🟠 **Partly AI-generated** | overall `real` **and** a core region exists (≥ 2 overlapping fake windows) | "Part of this clip (10–14 s) sounds AI-generated. Someone may have edited words in." + link to timeline |
| 🟡 Unclear | overall `real` and only one isolated fake window, **or** `scored_seconds` < 10 | "Too short or mixed to tell. Treat with care; ask the sender where it came from." |
| 🟢 No signs found | overall `real`, no fake windows | "No signs of an AI voice found. This checks the *voice*, not whether the claim is true." |

Always shown: "A score is evidence, not proof" (rule 03) + "works best on English and Hindi".
Errors: `422 insufficient_speech` → "Not enough speech to check" (no credits used);
> 300 s → check the first 5 minutes and say so; `402` → out of credits; `429/503` → retry with
the same Idempotency-Key after `Retry-After`.

---

## 4. Architecture

```
 Telegram group/DM ──► bot.py ─┐                         ┌─► cache hit? (file_unique_id, then Chromaprint ≥ 0.80)
                               ├─► core.check(audio) ────┤        └─► yes: stored result, "checked N times", 0 credits
 Android share sheet ─► api.py ┘   (normalise: ffmpeg     └─► no: POST /v1/deepfake/detect (Idempotency-Key = sha256)
   POST /share (PWA)                -vn mono 16 kHz Opus,            └─► verdict.py: band + core regions
                                    cap 300 s)                       └─► store in SQLite
                                                           ▼
                     reply: band text (en/hi/kn templates) + card PNG (Playwright) + link /r/<id>
                     /r/<id>: wavesurfer timeline, red core regions, transcript (EN, stretch)
```

Proposed layout (built during the hackathon, not before; owners in §5.3):
```
app/core/{normalize,aletheia,verdict,fingerprint,store,check,card}.py   app/i18n.json
app/api.py   app/bot.py   app/fixtures/*.json (mock results)
app/web/{result.html,card.html,theme.css,fonts/}   app/web/pwa/{manifest.webmanifest,sw.js}
tests/   submission/   CONTRACT.md   CLAUDE.md
```

---

## 5. Two-person split (each person drives their own Claude Code)

### 5.1 How the split works
- **Lane A — Engine & Web** (the "brain" + everything served over HTTPS): audio normalising,
  Aletheia client, verdict logic, cache, SQLite, FastAPI, result page with timeline, PWA.
- **Lane B — Bot, Card & Story** (everything the user sees in chat + everything judges read):
  Telegram bot, verdict card, Kannada/Hindi/English wording, README, Reddit post, demo video.
- The lanes meet at **one function and one JSON shape** (§5.2). A writes a **mock** of it in the
  first 30 minutes that replays the real Aletheia results already in `research/results/`, so B
  builds the whole bot against it without waiting for A — and without spending credits.
- **Each file has one owner** (§5.3), so two Claude Code sessions never edit the same file and
  git merges stay clean.
- Work happens on branches `lane-a` and `lane-b`; merge to `main` only at the 3 sync points.
- Credits: two accounts = two balances. Use **A's key for the product** (and the demo), **B's key
  for MCP testing** in Claude Code. Both develop with `MOCK_ALETHEIA` on.

### 5.2 The contract → now in `CONTRACT.md` (created 2026-11-25)
One `check()` function + one JSON shape (incl. `operation_id` for feedback), `send_feedback()`,
`render_card()`, the `app/i18n.json` format and mock mode (`MOCK_ALETHEIA=<fixture>|cycle`).
Change it only together. `tests/test_contract.py` keeps the mock honest.

### 5.3 Who owns which file
| Lane A owns | Lane B owns | Shared — change only at a sync point |
|---|---|---|
| `app/core/{normalize,aletheia,verdict,fingerprint,store,check}.py` | `app/bot.py` | `CONTRACT.md` |
| `app/api.py` | `app/core/card.py` | `requirements.txt` |
| `app/web/result.html`, `app/web/pwa/*` | `app/web/card.html`, `app/web/theme.css` | `env.example`, `app/config.py`, `app/fixtures/`, `tests/test_contract.py` |
| `tests/test_verdict.py`, `tests/test_cache.py` | `app/i18n.json` | `CLAUDE.md` (common part) |
| | `README.md`, `submission/*` | |

### 5.4 Steps

**Day 0 — preparation (accounts and tests only, no product code)**
| | Lane A | Lane B |
|---|---|---|
| D1 | Own DetectifAI account + API key (scopes `deepfake:detect`, `credits:read`); `GET /v1/credits` → note balance | Same, on your own account |
| D2 | ngrok account → claim the free **static domain**; confirm HTTPS reaches a local hello-world (the tunnel test we skipped) | @BotFather: create bot, `/setprivacy` → **Disable**; make a test group with both of you + the bot |
| D3 | Install stack (versions §2.7), `playwright install chromium`, `fpcalc` 1.5.1; check `research/spikes/` still run | **Accuracy test (most important):** with consent, record ~30 s real WhatsApp voice notes from both of you in English, Hindi, **Kannada**; one consented clone of your own voice; one spliced clip. Run them through Aletheia (MCP in Claude Code, or the 4 trial checks left). Write the results table into `research/real-world.md` |
| D4 | Android phone (whoever has one): confirm WhatsApp voice notes **and** videos offer "Share" to the system share sheet | Download Noto Sans Kannada + Devanagari fonts; read the chosen subreddit's rules (r/developersIndia or r/speechtech); draft the problem paragraph |
| D5 | Both: add the DetectifAI **MCP server** to Claude Code (command in §2.2) | |

**Kickoff — together, 30–45 min**
- [ ] K1. Push the base commit to a new GitHub repo, add the teammate as collaborator; each creates their lane branch
- [x] K2. `CONTRACT.md` + `CLAUDE.md` written (2026-11-25, in the base commit)
- [x] K3. Mock `check()` + fixtures + contract tests in the base commit; B branches from `main`

**Phase 1 — parallel (to the MVP)**
| Lane A | Lane B |
|---|---|
| - [x] A1. `normalize.py` (ffmpeg: drop video, mono 16 kHz Opus, cap 300 s) + `aletheia.py` (REST, Idempotency-Key = sha256 of normalised audio, error mapping). Done when all 6 `research/test-audio/` clips return real API results | - [ ] B1. `bot.py` on the mock: handlers for voice, audio, video, video_note, document in groups + DMs; download (refuse > 20 MB politely); call `check()`; reply with the band text. Done when the mock reply appears in the test group for a voice note **and** a video |
| - [x] A2. `verdict.py`: four bands + core regions (§3) + `tests/test_verdict.py` on the 6 fixtures. Done when spliced → `partly_fake` with `[[10.0, 14.0]]` | - [ ] B2. `i18n.json`: all four bands + errors in en/hi/kn (get the Kannada/Hindi checked by a native speaker); bot picks the language (default kn, `/lang en|hi|kn` per group) |

**🔁 Sync 1 — MVP:** merge both into `main`; turn the mock off; drop real clips in the group.
*Done when the spliced clip gets a 🟠 "partly AI-generated 10–14 s" reply from the real API.*
After this you always have a demo that works.

**Phase 2 — parallel (the wow)**
| Lane A | Lane B |
|---|---|
| - [x] A3. `store.py` (SQLite) + `fingerprint.py` (tier 1 `file_unique_id`, tier 2 Chromaprint ≥ 0.80) + `times_checked`; plus `send_feedback()` (store the 👍/👎 too). Done when the Opus copy of the spliced clip is a cache hit with `credits_charged: 0` | - [ ] B3. `card.html` + `theme.css` + `card.py` (Playwright, browser launched once at startup, ~25 ms per card); bot sends the card as a photo with the band text as caption |
| - [x] A4. `api.py` + `result.html`: `/r/<id>` with wavesurfer 7.12.12 (bundled locally), red core regions (click → plays the fake part), band text from `i18n.json`, honesty notes. Serve over the ngrok static domain | - [ ] B4. Cache-hit wording: "Already checked N times" + button linking to `result_url`; group etiquette: full reply for 🔴🟠🟡, short ✅ reply for 🟢; **"Was this right? 👍 / 👎" inline buttons** → `send_feedback()` (sends our users' corrections back to DetectifAI — mention it in the pitch) |

**🔁 Sync 2 — full flow:** merge; the card and the reply link to a live `/r/<id>` page.
*Done when one voice note in the group produces reply + card + working timeline link.*

**Phase 3 — parallel (finish + story)**
| Lane A | Lane B |
|---|---|
| - [x] A5. (code done; Chrome reports it installable; **Android install test still to do**) PWA: `manifest.webmanifest` with `share_target`, `sw.js`, `POST /share` → `check()` → redirect to `/r/<id>`; install on the Android phone. **Cut first if behind** | - [ ] B5. `README.md`: problem, how it works, how Aletheia is used (segments + core rule; MCP for dev), results table from `research/` + `research/real-world.md`, honest limits |
| - [ ] A6. Stretch: English transcript on the result page with the fake sentence highlighted (faster-whisper `base`) | - [ ] B6. Reddit post draft + screenshots/GIF; record a **backup demo video** from the Sync 2 build |
| - [x] A7. Hardening: errors (422, 402, 429/503 retry), > 300 s trim message, startup checks (keys present, `fpcalc` found, Chromium warm) | - [ ] B7. Write the 2-minute demo script into `submission/demo.md`; prepare the demo clips on both phones |

**🔁 Sync 3 — freeze:** merge; no new features after this.
- [ ] F1. Both: 3 full rehearsals on the venue network **and** on a mobile hotspot (A runs the server laptop, B drives the phones)
- [ ] F2. B: record the final 2-minute video; **post on Reddit (required, must be live before the Day-1 evaluation)**; reply to comments
- [ ] F3. A: tag the repo; check the README renders; fill the Google form with the Reddit link (+ X/LinkedIn if posted)

If you fall behind, cut in this order: A6 transcript → A5 PWA → B4 group etiquette. Never cut A2's
tests or the Reddit post.

### 5.5 Setting up each Claude Code session
The rules for both sessions are in the repo's `CLAUDE.md` (lane ownership, mock mode, secrets,
consent, facts not to re-test). Each person starts their session with one line:
- **A:** "I'm Lane A. Read PLAN.md §5 and CONTRACT.md, then do step A1. Stop when its *done when* check passes."
- **B:** "I'm Lane B. Read PLAN.md §5 and CONTRACT.md, then do step B1 against the mock. Stop when its *done when* check passes."

Then just move to the next step in your lane after each one passes.

### 5.7 Lane A — status, improvements and how to run (2026-11-25, branch `lane-a`)
**Done:** A1–A5 and A7 in code, 47 offline tests (fake Aletheia via `httpx.MockTransport`), plus a browser
end-to-end run: share upload → `/r/<id>` renders the waveform with the red region, Kannada text, feedback;
Chrome's installability check returns no errors. **Not done:** A6 (English transcript, stretch); the
real-API run (needs your key: `python -m scripts.smoke_real`, ≈ 200 credits); the Android install test.

**Improvements over the original plan (all tested):**
| Change | Why | Evidence |
|---|---|---|
| Send the original file when Aletheia accepts it; stream-copy audio out of videos; transcode only odd formats | no re-compression of evidence, much faster | voice note 48 ms vs 358 ms; MP4 94 ms vs 361 ms |
| Cache order: Telegram id (before decoding) → exact SHA-256 → fingerprint only if a stored clip has similar length; otherwise fingerprint **in parallel** with the API call | repeats cost nothing; new clips don't wait for fingerprinting | `tests/test_cache.py` |
| Single-flight for identical clips arriving together | one API call when a group forwards the same clip at once | `test_simultaneous_identical_clips_share_one_call` (also found and fixed a Windows file race) |
| Exact sweep over segment edges for the AI-sounding part (no time grid) | precise regions | spliced → `[[10.0, 14.0]]` |
| Retries reuse the Idempotency-Key (429/503/409/5xx/network), max 2 uploads at once | never charged twice, no 429 bursts | `test_rate_limit_is_retried_with_same_key` |
| SQLite in WAL mode with busy timeout | bot + web server are two processes on one DB | — |
| Mock results are stored too | Lane B's links open real pages without credits | `test_mock_mode_results_are_stored` |
| wavesurfer.js 7.12.12 bundled locally (not 8.1.1, published yesterday) | venue Wi-Fi / CDN can't break the demo; mature version | browser run, no console errors |
| `/health` lists demo-breaking problems (no key, no fpcalc, localhost URL) + DetectifAI status | 10-second pre-demo check | `test_health_reports_problems` |
| Feedback from the result page as well as the bot | more feedback for DetectifAI | `test_feedback_endpoint` |

**Run (Lane A machine = demo server):**
```bash
python -m pytest -q                         # 47 pass
python -m scripts.credits                   # key works? balance?
python -m scripts.smoke_real                # real API, ≈ 200 credits, expect ALL GOOD
uvicorn app.api:app --host 127.0.0.1 --port 8000
ngrok http --url=<your-static-domain> 8000  # then PUBLIC_BASE_URL=https://<your-static-domain> in .env
# open https://<your-static-domain>/health → "ok": true, "issues": []
```

### 5.6 Submission checklist (owner in brackets)
- [ ] S1. Repo + README [B writes, A reviews]
- [ ] S2. 2-minute demo video [B]
- [ ] S3. **Reddit post live before evaluation** [B], replies to comments [both]
- [ ] S4. Google form with team details + Reddit link [A]
- [ ] S5. Optional: X quote-post of Tarini's post / LinkedIn post tagging DetectifAI [either]

---

## 6. Two-minute demo script
1. **Hook (15 s):** "Every college group has seen a fake *holiday tomorrow* voice note. Now they can be AI-made — or worse, a real recording with one sentence swapped."
2. Drop a fully fake announcement into the Telegram group → 🔴 reply in Kannada + card (idea 3, 6).
3. Drop the **spliced** clip → 🟠 "Part of this clip (10–14 s) sounds AI-generated" → tap → timeline, click the red region, hear the fake sentence (idea 1). Say plainly: *the model's overall verdict alone said real; reading its segments is what caught it.*
4. On Android: WhatsApp → Share → our app → instant "already checked" (ideas 4, 7).
5. A real teammate voice note → 🟢, plus one short clip → 🟡 Unclear. Honest results on stage.

---

## 7. Risks and what we do about them
| Risk | Mitigation |
|---|---|
| Real voice clones harder to catch than Edge TTS | D4 tests it; pitch says "evidence, not proof" |
| False alarms on real Kannada / phone voice notes | D4 measures it; 🟡 band; ≥ 10 s guidance in replies |
| Venue Wi-Fi / tunnel fails | mobile hotspot; pre-recorded demo video; static ngrok domain |
| Credits run out in rehearsal | cache + Idempotency-Key; short clips; watch `GET /v1/credits` |
| Bot sees nothing in the group | privacy mode disabled **and bot re-added** (D2) |
| Chromium cold start (1.9 s) | launch once at boot, reuse the page |
| PWA breaks after the URL changes | static domain only |
| Long videos | Telegram cap 20 MB; Aletheia cap 300 s → trim and say so |

## Constraints and decisions
- Track 4, Aletheia only; ideas 1+3+4+6+7 (team decision, 2026-11-24).
- One Aletheia call per clip; segments come from the API. No client-side windowing.
- Partly-fake detection = ≥ 2 overlapping fake windows (tested: 10–14 s vs truth 10.0–14.8 s).
- Cards and timeline are HTML (Pillow can't shape Kannada).
- Only consented voices are cloned (own/teammates); generic TTS voices for synthetic samples.
- Never commit API keys or bot tokens; `.env` only.
- Team of 2, each with Claude Code: Lane A (engine + web) and Lane B (bot + card + story), joined by `CONTRACT.md`; one owner per file; mock mode first.
- REST API in the product; MCP only inside Claude Code for development.

## Open questions
- How many build hours on Day 1? (sets how far past Sync 2 we get)
- Who has the Android phone? (that person tests D4/A5; swap A5 to them if it's B)
- Hackathon credit balance per account? (D1)
- Real Kannada voice-note false-alarm rate? (D4 — could change how prominent Kannada is in the pitch)
- Product name? ("Check Before Share" is a placeholder; a Kannada/Hindi name could help the pitch)
- Is the Twilio WhatsApp sandbox worth having as an iPhone fallback?
