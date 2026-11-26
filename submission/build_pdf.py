"""Render submission/explainer.html to submission/check-before-share-explainer.pdf (A4, Playwright).

    python submission/build_pdf.py [--png]      # --png also writes page previews to the scratch dir given
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "explainer.html"
OUT = HERE / "check-before-share-explainer.pdf"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.goto(SRC.as_uri())
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.pdf(path=str(OUT), format="A4", print_background=True, prefer_css_page_size=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--png":
        page.set_viewport_size({"width": 794, "height": 1123})
        for i, el in enumerate(page.query_selector_all("section.page")):
            el.screenshot(path=str(Path(sys.argv[2]) / f"page{i + 1:02d}.png"))
    b.close()
print(OUT)
