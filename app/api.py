"""Lane A · steps A4 + A5 — web server. Run: uvicorn app.api:app --port 8000

  GET  /                     landing page: upload form + "install the app" hint
  POST /share                upload (form field "media", also the PWA share target) → 303 /r/{id}
  POST /api/check            upload (field "file") → CONTRACT JSON
  GET  /api/result/{id}      CONTRACT JSON
  POST /api/feedback/{id}    {"correct": bool, "label": "real"|"fake"|null}
  GET  /r/{id}               result page (waveform, AI-sounding part in red, verdict in kn/hi/en)
  GET  /media/{id}           the checked audio, for the waveform
  GET  /radar, /api/radar    AI-clip radar: flagged clips that are circulating (2+ chats or 3+ checks)
  GET  /manifest.webmanifest, /sw.js, /offline, /static/*   PWA + assets
  GET  /health               self-check: mock mode, key, fpcalc, public URL, DetectifAI status, stats
"""
import json
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import config
from app.core import aletheia, check as check_mod, fingerprint, store

log = logging.getLogger("app.api")
WEB = config.WEB_DIR
MAX_UPLOAD = 200 * 1024 * 1024
LANGS = ("kn", "hi", "en")


def startup_report() -> list[str]:
    """Problems that would break the demo, in plain words (also logged at startup)."""
    issues = []
    if not config.MOCK_ALETHEIA and not config.DETECTIF_API_KEY:
        issues.append("DETECTIF_API_KEY is empty and MOCK_ALETHEIA is off: every check will fail")
    if not fingerprint.fpcalc_path():
        issues.append("fpcalc not found: re-encoded forwards won't hit the cache (exact repeats still will)")
    if "localhost" in config.PUBLIC_BASE_URL or "127.0.0.1" in config.PUBLIC_BASE_URL:
        issues.append("PUBLIC_BASE_URL is localhost: result links in Telegram won't open on phones")
    return issues


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    mode = f"MOCK ({config.MOCK_ALETHEIA})" if config.MOCK_ALETHEIA else "LIVE (real Aletheia API)"
    log.info("Check Before Share API — %s — public URL %s", mode, config.PUBLIC_BASE_URL)
    for issue in startup_report():
        log.warning(issue)
    yield


app = FastAPI(title="Check Before Share", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


# --------------------------------------------------------------------------- helpers

def _i18n() -> dict:
    return {k: v for k, v in json.loads(config.I18N_PATH.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def _embed(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


async def _save_upload(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "upload").suffix[:10]
    fd, tmp = tempfile.mkstemp(suffix=suffix, dir=config.DB_PATH.parent if config.DB_PATH.parent.exists() else None)
    size = 0
    with os.fdopen(fd, "wb") as out:
        while chunk := await upload.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD:
                out.close()
                os.remove(tmp)
                raise HTTPException(413, "File too large (max 200 MB)")
            out.write(chunk)
    return tmp


async def _check_upload(upload: UploadFile, channel: str) -> dict:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = await _save_upload(upload)
    try:
        return await check_mod.check(tmp, source={"channel": channel, "tg_file_unique_id": None,
                                                  "filename": upload.filename or "upload"})
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _media_allowed(path: Path) -> bool:
    allowed = [(config.DB_PATH.parent / "audio").resolve(), (config.ROOT / "research" / "test-audio").resolve()]
    rp = path.resolve()
    return any(rp.is_relative_to(a) for a in allowed)


NO_STORE = {"Cache-Control": "no-store"}


# --------------------------------------------------------------------------- pages

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))


@app.get("/r/{check_id}", response_class=HTMLResponse)
def result_page(check_id: str, lang: str | None = None):
    r = store.get(check_id)
    if not r:
        return HTMLResponse("<!doctype html><meta name=viewport content='width=device-width'>"
                            "<p style='font-family:system-ui;padding:24px'>This result doesn't exist (or was deleted). "
                            "<a href='/'>Check a clip</a></p>", status_code=404)
    path = store.audio_path(check_id)
    r["has_audio"] = bool(path and Path(path).exists())
    lang = lang if lang in LANGS else (config.DEFAULT_LANG if config.DEFAULT_LANG in LANGS else "en")
    html = ((WEB / "result.html").read_text(encoding="utf-8")
            .replace("__DATA__", _embed(r)).replace("__I18N__", _embed(_i18n())).replace("__LANG__", lang))
    return HTMLResponse(html, headers=NO_STORE)


@app.get("/radar", response_class=HTMLResponse)
def radar_page():
    return HTMLResponse((WEB / "radar.html").read_text(encoding="utf-8")
                        .replace("__I18N__", _embed({k: v for k, v in _i18n().items() if k.startswith("label_")})))


@app.get("/api/radar")
def api_radar():
    return JSONResponse(store.radar(), headers={"Cache-Control": "no-store"})


@app.get("/offline", response_class=HTMLResponse)
def offline():
    return HTMLResponse("<!doctype html><meta name=viewport content='width=device-width'><title>Offline</title>"
                        "<p style='font-family:system-ui;padding:24px'>You're offline. Connect to the internet "
                        "and share the clip again.</p>")


@app.get("/media/{check_id}")
def media(check_id: str):
    path = store.audio_path(check_id)
    if not path or not Path(path).exists() or not _media_allowed(Path(path)):
        raise HTTPException(404, "No audio for this result")
    return FileResponse(path)


# --------------------------------------------------------------------------- PWA

@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB / "pwa" / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(WEB / "pwa" / "sw.js", media_type="text/javascript",
                        headers={"Service-Worker-Allowed": "/", **NO_STORE})


@app.get("/favicon.ico")
def favicon():
    return FileResponse(WEB / "static" / "icons" / "icon-192.png", media_type="image/png")


@app.post("/share")
async def share(media: UploadFile = File(...)):
    r = await _check_upload(media, "share")
    return RedirectResponse(f"/r/{r['id']}", status_code=303)


# --------------------------------------------------------------------------- JSON API

@app.post("/api/check")
async def api_check(file: UploadFile = File(...)):
    return await _check_upload(file, "api")


@app.get("/api/result/{check_id}")
def api_result(check_id: str):
    r = store.get(check_id)
    if not r:
        raise HTTPException(404, "Unknown result id")
    return r


class Feedback(BaseModel):
    correct: bool
    label: str | None = None


@app.post("/api/feedback/{check_id}")
async def api_feedback(check_id: str, fb: Feedback):
    if not store.get(check_id):
        raise HTTPException(404, "Unknown result id")
    await check_mod.record_feedback(check_id, fb.correct, fb.label, channel="web")
    return {"ok": True}


@app.get("/health")
async def health():
    return JSONResponse({
        "ok": not startup_report() or bool(config.MOCK_ALETHEIA),
        "mode": f"mock:{config.MOCK_ALETHEIA}" if config.MOCK_ALETHEIA else "live",
        "api_key_set": bool(config.DETECTIF_API_KEY),
        "fpcalc": bool(fingerprint.fpcalc_path()),
        "public_base_url": config.PUBLIC_BASE_URL,
        "issues": startup_report(),
        "detectif": await aletheia.health(),
        "stats": store.stats(),
    }, headers=NO_STORE)
