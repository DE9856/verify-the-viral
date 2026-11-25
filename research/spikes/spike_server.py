"""THROWAWAY spike: does a share-target style multipart POST reach FastAPI, and does the
ffmpeg -> fingerprint path work for audio + video uploads? No Aletheia call (no key)."""
import json, os, subprocess, tempfile, time
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPCALC = os.path.abspath("dl/fpcalc/chromaprint-fpcalc-1.5.1-windows-x86_64/fpcalc.exe")
app = FastAPI()

MANIFEST = {
    "name": "Check Before Share", "short_name": "CheckShare", "start_url": "/", "display": "standalone",
    "background_color": "#101418", "theme_color": "#101418",
    "icons": [{"src": "/icon.png", "sizes": "512x512", "type": "image/png"}],
    "share_target": {"action": "/share", "method": "POST", "enctype": "multipart/form-data",
                     "params": {"title": "title", "text": "text", "files": [
                         {"name": "media", "accept": ["audio/*", "video/*", ".ogg", ".opus", ".mp4", ".m4a"]}]}},
}


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(MANIFEST, media_type="application/manifest+json")


@app.get("/", response_class=HTMLResponse)
def home():
    return '<link rel="manifest" href="/manifest.webmanifest"><h1>spike</h1>'


@app.post("/share")
async def share(media: UploadFile = File(...)):
    t0 = time.time()
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "in_" + os.path.basename(media.filename or "upload"))
        open(src, "wb").write(await media.read())
        out = os.path.join(d, "audio.ogg")
        # one normalising step for everything: drop video, mono, 16 kHz, opus, cap at 300 s (Aletheia max)
        subprocess.run([FF, "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-t", "300",
                        "-c:a", "libopus", "-b:a", "32k", out], check=True)
        t1 = time.time()
        fp = json.loads(subprocess.run([FPCALC, "-json", "-length", "300", out], capture_output=True, check=True).stdout)
        return {"received": media.filename, "content_type": media.content_type, "in_bytes": os.path.getsize(src),
                "normalised_bytes": os.path.getsize(out), "duration": fp["duration"],
                "ffmpeg_ms": round(1000 * (t1 - t0)), "total_ms": round(1000 * (time.time() - t0)),
                "fingerprint_prefix": fp["fingerprint"][:24]}
