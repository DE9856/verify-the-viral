"""Lane B · B3 — verdict card as PNG (CONTRACT.md §3).

app/web/card.html is loaded ONCE into a warm Playwright Chromium page; each card is
window.render(data) + a screenshot (tens of ms warm, ~2 s cold start).
Not Pillow: it breaks Kannada and Hindi shaping. Fonts are local in app/web/fonts/.
Call start() at bot startup (optional; render_card starts lazily) and close() at shutdown.
"""
import asyncio
import json
import math

from playwright.async_api import async_playwright

from app import config

WIDTH, HEIGHT = 900, 420
SCALE = 2          # render at 2x so text stays sharp on phones (PNG is 1800×840)
BIN_SECONDS = 0.25

_I18N = json.loads(config.I18N_PATH.read_text(encoding="utf-8"))
_state: dict = {}
_lock = asyncio.Lock()


def _t(key: str, lang: str, **kw) -> str:
    entry = _I18N.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kw) if kw else text


def _fmt_s(x: float) -> str:
    return f"{x:.0f}" if x >= 3 else f"{x:.1f}".rstrip("0").rstrip(".")


def timeline_bins(segments: list, duration: float, step: float = BIN_SECONDS) -> list[int]:
    """Per time slice: how many fake windows cover it, capped at 2 (2 = the 'core region' rule)."""
    if not segments or not duration:
        return []
    n = max(1, math.ceil(duration / step))
    bins = []
    for i in range(n):
        mid = (i + 0.5) * step
        hits = sum(1 for s in segments if s.get("verdict") == "fake" and s["start"] <= mid < s["end"])
        bins.append(min(hits, 2))
    return bins


def card_data(result: dict, lang: str) -> dict:
    """Everything card.html needs, already translated. Pure function, easy to test."""
    band = result["band"]
    unit = _t("seconds", lang)
    regions = ", ".join(f"{a:g}–{b:g} {unit}" for a, b in result.get("core_regions", []))
    duration = result.get("duration") or 0
    return {
        "lang": lang,
        "band": band,
        "label": _t(f"label_{band}", lang),
        "advice": _t(f"advice_{band}", lang, regions=regions),
        # the splice story in one line: the whole-clip verdict said real, the segments caught it
        "note": _t("card_overall_note", lang)
        if band == "partly_fake" and (result.get("overall") or {}).get("verdict") == "real" else "",
        "timeline_label": _t("card_timeline", lang),
        "legend_ai": _t("legend_ai", lang),
        "legend_human": _t("legend_human", lang),
        "disclaimer": _t("disclaimer", lang),
        "checked_by": _t("checked_by", lang),
        "test": _t("card_test", lang) if config.MOCK_ALETHEIA else "",
        "bins": timeline_bins(result.get("segments", []), duration),
        "axis_mid": f"{_fmt_s(duration / 2)} {unit}" if duration else "",
        "axis_end": f"{_fmt_s(duration)} {unit}" if duration else "",
    }


async def start() -> None:
    """Launch Chromium once and load the template (idempotent)."""
    if _state.get("page"):
        return
    pw = await async_playwright().start()
    browser = await pw.chromium.launch()
    page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=SCALE)
    await page.goto((config.WEB_DIR / "card.html").as_uri())
    await page.evaluate("document.fonts.ready.then(() => true)")
    _state.update(pw=pw, browser=browser, page=page)


async def close() -> None:
    if _state.get("browser"):
        await _state["browser"].close()
        await _state["pw"].stop()
    _state.clear()


async def render_card(result: dict, lang: str = "kn") -> bytes:
    """PNG bytes of the verdict card. Not for band == "error" (send text instead)."""
    if result["band"] == "error":
        raise ValueError("no card for errors")
    async with _lock:  # one shared page
        await start()
        page = _state["page"]
        await page.evaluate("d => window.render(d)", card_data(result, lang))
        return await page.screenshot(type="png")
