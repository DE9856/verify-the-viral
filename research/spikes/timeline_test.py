"""Timeline (idea 1): compare wavesurfer.js+regions vs plain per-second heat strip, on the real
spliced_en trial result. Also tests the 'core region' rule: seconds covered by >=2 fake windows."""
import json, threading, http.server, functools, time
from playwright.sync_api import sync_playwright

res = json.loads(json.load(open("results/spliced_en.json", encoding="utf-8"))["result"]["content"][0]["text"])["result"]
segs, dur = res["segments"], res["duration_seconds"]

# per-0.5s max score + fake-window coverage count
step = 0.5
cells = []
t = 0.0
while t < dur:
    cov = [s for s in segs if s["start"] <= t + step / 2 < s["end"]]
    cells.append((t, max(s["score"] for s in cov) if cov else 0, sum(s["verdict"] == "fake" for s in cov)))
    t += step
core, cur = [], None
for t, sc, n in cells:
    if n >= 2 and cur is None: cur = t
    if n < 2 and cur is not None: core.append((cur, t)); cur = None
if cur is not None: core.append((cur, dur))
any_fake = [(s["start"], s["end"]) for s in segs if s["verdict"] == "fake"]
print("ground truth fake: 10.0-14.8 s")
print("any fake window  :", (min(a for a, _ in any_fake), max(b for _, b in any_fake)))
print("core (>=2 windows):", core)

strip = "".join(f'<div style="flex:1;background:hsl({120 - 120*sc:.0f} 70% 45%)" title="{t:.1f}s {sc:.2f}"></div>' for t, sc, n in cells)
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{font-family:system-ui;background:#101418;color:#e6e9ec;margin:24px;width:860px}} h3{{margin:18px 0 8px;font-weight:600;font-size:15px;color:#9aa6b2}}
.strip{{display:flex;height:34px;border-radius:6px;overflow:hidden}} #ws{{background:#161c22;border-radius:6px}}</style></head><body>
<h3>A. wavesurfer.js 7 + regions (playable waveform, red = core fake region)</h3><div id="ws"></div>
<h3>B. plain per-0.5 s heat strip (no library; same markup works inside the verdict card)</h3><div class="strip">{strip}</div>
<script type="module">
import WaveSurfer from 'https://unpkg.com/wavesurfer.js@7.8.6/dist/wavesurfer.esm.js'
import Regions from 'https://unpkg.com/wavesurfer.js@7.8.6/dist/plugins/regions.esm.js'
const regions = Regions.create()
const ws = WaveSurfer.create({{container:'#ws', url:'audio/spliced_en.wav', height:90, waveColor:'#5b6b7a', progressColor:'#8fa3b5', plugins:[regions]}})
ws.on('decode', () => {{ {''.join(f"regions.addRegion({{start:{a},end:{b},color:'rgba(229,72,77,.35)',drag:false,resize:false}});" for a,b in core)} document.title='ready' }})
</script></body></html>"""
open("timeline.html", "w", encoding="utf-8").write(html)

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8766), handler)  # localhost only
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 910, "height": 300})
    t0 = time.time(); pg.goto("http://127.0.0.1:8766/timeline.html"); pg.wait_for_function("document.title==='ready'", timeout=20000)
    print(f"wavesurfer ready in {1000*(time.time()-t0):.0f} ms"); pg.wait_for_timeout(300)
    pg.screenshot(path="timeline.png"); b.close()
srv.shutdown()
