"""Lane B · step B3 — verdict card as PNG (CONTRACT.md §3).

Tested approach (research/spikes/card_test.py, research/screenshots/card_html.png):
fill app/web/card.html → render with Playwright Chromium → screenshot 900×420.
Launch the browser ONCE at startup and reuse a page (~25 ms per card warm, ~1.9 s cold).
Do not use Pillow for text: it breaks Kannada and Hindi shaping.
Load fonts from app/web/fonts/ (Noto Sans Kannada + Devanagari), not from Google, so venue Wi-Fi can't break it.
"""


async def render_card(result: dict, lang: str = "kn") -> bytes:
    raise NotImplementedError("Lane B · B3: render_card()")
