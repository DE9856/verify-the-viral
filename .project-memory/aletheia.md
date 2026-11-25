# Aletheia (updated 2026-11-26)
- REST in the product; MCP only inside Claude Code (base64, 25 MB, LLM round trip).
- One call returns 4 s windows every 2 s; never window client-side. Partly-fake = seconds covered by ≥ 2 overlapping fake windows.
- Read each window's `verdict` field (own threshold: a 0.883 window came back real), never score > 0.62.
- Limits (docs): ≤ 300 s (longer = 422 audio_too_long), ≥ 2 s speech (422 insufficient_speech, not charged), 2 credits/s, min 20 per check. OGG/Opus accepted; ffmpeg only to strip video / odd formats.
- Live stream: `wss://platform.detectif.ai/v1/stream?checks=deepfake`, 16 kHz PCM, key in a header (never in the URL), early verdict at 4.5–8 s of speech, updates every `update_seconds` (we use 5), only speech seconds billed, segment times = stream time (duration_seconds = speech length).
- Through a speaker → phone mic, real speech came back "fake" for 2–4 s (0.65–0.97, varies per run; the same file checks clean). Live bands use `verdict.decide_live` (≥ 3 overlapping fake windows each ≥ 0.9); score floors overfit (`research/live-listen.md`).
