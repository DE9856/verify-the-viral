"""Verdict card (idea 6): Pillow vs HTML->PNG (Playwright). Uses the real spliced_en trial result."""
import json, time
from PIL import Image, ImageDraw, ImageFont

KN = "ಎಚ್ಚರಿಕೆ: ಈ ಧ್ವನಿಯ ಒಂದು ಭಾಗ ಕೃತಕವಾಗಿ ರಚಿಸಲ್ಪಟ್ಟಿರಬಹುದು"
HI = "सावधान: इस आवाज़ का एक हिस्सा AI से बना हो सकता है"
EN = "Part of this clip sounds AI-generated (8–16 s)"

res = json.loads(json.load(open("results/spliced_en.json", encoding="utf-8"))["result"]["content"][0]["text"])["result"]
segs, dur = res["segments"], res["duration_seconds"]

# ---------------- A: Pillow (basic layout, no raqm) ----------------
t0 = time.time()
img = Image.new("RGB", (900, 420), "#101418")
d = ImageDraw.Draw(img)
f_kn = ImageFont.truetype(r"C:\Windows\Fonts\Nirmala.ttc", 34, index=0)
f_en = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 30)
d.text((30, 30), "PARTLY AI-GENERATED", font=f_en, fill="#ffb020")
d.text((30, 90), KN, font=f_kn, fill="white")
d.text((30, 150), HI, font=f_kn, fill="white")
d.text((30, 210), EN, font=f_en, fill="#c8d0d8")
for s in segs:
    x0, x1 = 30 + 840 * s["start"] / dur, 30 + 840 * s["end"] / dur
    d.rectangle([x0, 300, x1, 340], fill="#e5484d" if s["verdict"] == "fake" else "#2f9e66")
img.save("card_pillow.png")
print(f"pillow: {1000*(time.time()-t0):.0f} ms")

# ---------------- B: HTML -> PNG with Playwright ----------------
bars = "".join(
    f'<div style="position:absolute;left:{100*s["start"]/dur:.2f}%;width:{100*(s["end"]-s["start"])/dur:.2f}%;'
    f'height:100%;background:{"#e5484d" if s["verdict"]=="fake" else "#2f9e66"};opacity:{0.35+0.65*s["score"] if s["verdict"]=="fake" else 0.5}"></div>'
    for s in segs)
html = f"""<html><head><link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Kannada:wght@500;700&family=Noto+Sans+Devanagari:wght@500&family=Inter:wght@500;700&display=swap" rel="stylesheet">
<style>body{{margin:0;width:900px;height:420px;background:#101418;color:#fff;font-family:Inter,'Noto Sans Kannada','Noto Sans Devanagari',sans-serif}}
.c{{padding:30px}} .tag{{color:#ffb020;font-weight:700;font-size:28px;letter-spacing:.04em}}
.kn{{font-family:'Noto Sans Kannada';font-size:32px;margin-top:18px}} .hi{{font-family:'Noto Sans Devanagari';font-size:30px;margin-top:8px}}
.en{{color:#c8d0d8;font-size:26px;margin-top:8px}} .tl{{position:relative;height:40px;margin-top:34px;background:#1c232b;border-radius:6px;overflow:hidden}}
.ax{{display:flex;justify-content:space-between;color:#8a96a3;font-size:16px;margin-top:6px}}</style></head>
<body><div class="c"><div class="tag">⚠ PARTLY AI-GENERATED</div><div class="kn">{KN}</div><div class="hi">{HI}</div>
<div class="en">{EN}</div><div class="tl">{bars}</div><div class="ax"><span>0 s</span><span>{dur:.0f} s</span></div></div></body></html>"""
open("card.html", "w", encoding="utf-8").write(html)

from playwright.sync_api import sync_playwright
t0 = time.time()
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 900, "height": 420})
    pg.set_content(html, wait_until="networkidle")
    t1 = time.time()
    pg.screenshot(path="card_html.png")
    # second render on a warm browser = steady-state cost per card
    pg.set_content(html, wait_until="networkidle"); t2 = time.time(); pg.screenshot(path="card_html2.png"); t3 = time.time()
    b.close()
print(f"playwright: cold {1000*(t1-t0):.0f} ms (incl. launch + font fetch), warm {1000*(t3-t2):.0f} ms")
