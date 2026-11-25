# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Anyone who receives a forwarded voice note or video and wonders whether it is real: people in
family, apartment and college WhatsApp/Telegram groups in Karnataka and across India, from students
to grandparents. Usually one tech-comfortable member adds the bot to the group; everyone in the
group reads its replies. Hackathon judges (CMRIT × DetectifAI, Track 4) and Reddit readers see the
same screens in the demo and the write-up. Confirmed by the user: design for all of them, any user.

## Product Purpose

Check Before Share checks voice notes and videos for AI-generated voices with DetectifAI's Aletheia
model, says in plain words whether to trust them, and shows *which seconds* sound fake, so the
fact-check travels back into the group instead of the fake. Success: people stop forwarding a fake
because the answer reached them first, in their language.

## Positioning

It reads Aletheia's 4-second window scores, not just the overall verdict. In our tests a real
recording with one cloned sentence pasted in got an overall verdict of *real*; the windows caught it
and we named the seconds (English 10–14 s, Kannada 14–16 s). It also lives where the fakes spread:
inside the group chat, in Kannada, Hindi and English.

## Operating Context

- Telegram group or DM: the bot replies to a voice note, audio, video or round video with a verdict
  card image (PNG, rendered from `app/web/card.html` by Playwright Chromium) plus caption text, a
  "See where in the clip" button and 👍/👎 feedback buttons. In groups a clean 🟢 result gets one
  quiet line instead of a card.
- Result page `/r/<id>` (`app/web/result.html`): waveform of the clip (wavesurfer.js 7.12.12, bundled)
  with the AI-sounding part marked; tap it to hear the fake sentence; feedback buttons.
- Android share sheet: an installable PWA (`app/web/index.html`, `app/web/pwa/`) so people can share
  a WhatsApp voice note straight to the checker.
- Phones first: cards are viewed in chat on small screens; pages are opened from Telegram on phones.
  Shown on a projector in a 2-minute live demo.

## Capabilities and Constraints

- Four verdict bands, exact terms: 🔴 Likely AI-generated · 🟠 Partly AI-generated (with the
  seconds) · 🟡 Unclear (too short or mixed) · 🟢 No signs of an AI voice. Plus error replies.
- Languages: English (default), Hindi, Kannada; all wording comes from `app/i18n.json`, shared by the
  bot, card and result page. Kannada and Hindi must shape correctly: text is rendered by Chromium
  with bundled Noto fonts (`app/web/fonts/`), never Pillow.
- No dependence on venue Wi-Fi: fonts and scripts are bundled locally, no CDN at runtime.
- The card is a fixed-size image (contract: ~900×420, rendered at 2×), so it must read at
  thumbnail size inside a chat bubble.
- Limits: Telegram bot downloads ≤ 20 MB; Aletheia checks ≤ 300 s (first 5 minutes, said so).
- Test mode (`MOCK_ALETHEIA`) marks cards "TEST SAMPLE".
- Ownership: card files are Lane B's; result and landing pages are Lane A's (redesign agreed by the
  user for both, 2026-11-25).

## Brand Commitments

- Name: **Check Before Share** (confirmed, final).
- Voice: plain, calm, honest. Every verdict says what to do next ("Don't forward it…", "Ask the
  sender where it came from"). Always "a score is evidence, not proof" and "this checks the voice,
  not whether the claim is true".
- Credit line: "Checked with Aletheia by DetectifAI".

## Evidence on Hand

- `research/real-world.md`: real voices 12/12 called real; consented clones 6/6 caught; real notice +
  one cloned sentence 6/6 flagged (overall verdict alone missed English and Kannada).
- `research/results/`, `app/fixtures/`: recorded real Aletheia responses usable as demo data.
- `submission/img/`: card renders used by the README.
- No users, testimonials, partners or usage numbers exist; never invent them.

## Product Principles

1. The answer first, in the reader's language: one glance should tell a grandparent whether to
   forward.
2. Honest by design: evidence, not proof; say when we can't tell; never overstate.
3. Show *where*, not just *whether*: the seconds are the product's unique value.
4. Built to be forwarded: the card has to survive being a small image in a busy group chat.
5. Works offline from the venue: nothing essential loads from the internet at view time.

## Accessibility & Inclusion

Readers include older people on small phones: large type, strong contrast (WCAG AA minimum), meaning
never carried by colour alone (each band also has a word and an emoji), and correct Kannada and
Devanagari shaping.
