# Research spikes (2026-11-24)

Throwaway tests behind the decisions in `../PLAN.md`. Not product code.

| Path | What |
|---|---|
| `spikes/mcp_trial.py` | Minimal MCP client for the free DetectifAI trial (`list`, or `detect <files>`; each file = 1 of 10 trial checks per network, 4 left) |
| `spikes/fp_test.py` | Fingerprint comparison: SHA vs Chromaprint vs numpy Philips hash |
| `spikes/card_test.py` | Verdict card: Pillow vs HTML→PNG (Playwright) with Kannada/Hindi text |
| `spikes/timeline_test.py` | wavesurfer.js regions vs heat strip; core-region rule |
| `spikes/stt_test.py` | faster-whisper word timestamps (EN/HI/KN) |
| `spikes/spike_server.py` | Share-target style multipart POST → ffmpeg → fpcalc |
| `results/*.json` | Raw Aletheia responses for the six test clips |
| `screenshots/` | Card and timeline renders |
| `test-audio/` | Test clips: public-domain human speech (Open Speech Repository) + Edge neural TTS. Spliced clip has the fake at 10.0–14.8 s |

To rerun: the scripts expect `audio/`, `results/` and `dl/fpcalc/chromaprint-fpcalc-1.5.1-windows-x86_64/fpcalc.exe`
next to them (copy `test-audio/` to `audio/`). Python 3.11 venv with:
`pip install httpx edge-tts imageio-ffmpeg numpy scipy pillow fastapi uvicorn python-multipart playwright faster-whisper`
then `playwright install chromium`.
