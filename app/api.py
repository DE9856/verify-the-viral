"""Lane A · step A4 (+ A5 PWA) — web server. Run: uvicorn app.api:app --port 8000

To build:
- POST /api/check (multipart "file") → check() → CONTRACT JSON
- GET  /r/{id}    → result page (app/web/result.html): wavesurfer.js 7.8.6 timeline, red core regions,
                    band text from app/i18n.json, honesty notes
- A5: GET /manifest.webmanifest, /sw.js, POST /share (multipart "media") → check() → redirect /r/{id}
      (tested shape: research/spikes/spike_server.py)
"""
from fastapi import FastAPI

from app import config

app = FastAPI(title="Check Before Share")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "mock": config.MOCK_ALETHEIA or None,
            "api_key_set": bool(config.DETECTIF_API_KEY)}
