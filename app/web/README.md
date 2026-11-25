# app/web

| File | Owner | What |
|---|---|---|
| `result.html` | Lane A | Result page `/r/<id>`: waveform with the AI-sounding part in red, segment heat strip, verdict in kn/hi/en, feedback |
| `index.html` | Lane A | Landing page `/`: upload form + install hint + radar link |
| `radar.html` | Lane A | Fake radar `/radar`: flagged clips that are circulating, live (polls `/api/radar`) |
| `pwa/manifest.webmanifest`, `pwa/sw.js` | Lane A | Installable app + Android share target (`POST /share`) |
| `static/vendor/wavesurfer-7.12.12/` | Lane A | wavesurfer.js + regions plugin, bundled locally (BSD-3, see LICENSE) so venue Wi-Fi can't break it |
| `static/icons/` | Lane A | App icons (192, 512) |
| `card.html`, `theme.css` | Lane B | B3: verdict card template (prototype: `research/spikes/card_test.py`) |
| `fonts/` | Lane B | Noto Sans Kannada + Noto Sans Devanagari (woff2), served locally |
