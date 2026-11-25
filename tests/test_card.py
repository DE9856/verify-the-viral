"""Lane B · B3: card data (pure) + one real render through Chromium."""
import asyncio
import json

import pytest

from app import config
from app.core import card
from app.core import check as check_mod

EXPECTED = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))


def mock_result(monkeypatch, name):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", name)
    return asyncio.run(check_mod.check("x.ogg", source={"channel": "telegram",
                                                        "tg_file_unique_id": None, "filename": "x.ogg"}))


def test_bins_follow_the_core_rule():
    segs = [{"start": 8.0, "end": 12.0, "verdict": "fake"}, {"start": 10.0, "end": 14.0, "verdict": "fake"},
            {"start": 0.0, "end": 4.0, "verdict": "real"}]
    bins = card.timeline_bins(segs, 16.0, step=1.0)
    assert bins[:8] == [0] * 8 and bins[8:10] == [1, 1] and bins[10:12] == [2, 2] and bins[12:14] == [1, 1]
    assert card.timeline_bins([], 10.0) == [] and card.timeline_bins(segs, 0) == []


@pytest.mark.parametrize("lang", ["en", "hi", "kn"])
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_card_data_is_complete_and_translated(monkeypatch, name, lang):
    d = card.card_data(mock_result(monkeypatch, name), lang)
    for key in ["label", "advice", "timeline_label", "legend_ai", "legend_human", "disclaimer", "checked_by"]:
        assert d[key] and "{" not in d[key], key
    assert d["bins"] and d["test"]  # mock mode → TEST SAMPLE badge
    assert "." not in d["axis_mid"].split()[0] or float(d["axis_mid"].split()[0]) < 3


def test_partly_fake_card_names_the_seconds(monkeypatch):
    assert "10–14 ಸೆಕೆಂಡು" in card.card_data(mock_result(monkeypatch, "spliced_en"), "kn")["advice"]


def test_render_png(monkeypatch):
    result = mock_result(monkeypatch, "spliced_en")

    async def go():
        try:
            return await card.render_card(result, "kn")
        finally:
            await card.close()
    png = asyncio.run(go())
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 20_000


def test_no_card_for_errors(monkeypatch):
    with pytest.raises(ValueError):
        asyncio.run(card.render_card(mock_result(monkeypatch, "error_failed"), "en"))


def test_partly_fake_card_says_the_whole_clip_verdict_missed_it(monkeypatch):
    note = card.card_data(mock_result(monkeypatch, "spliced_en"), "en")["note"]
    assert "Whole-clip verdict alone: real" in note
    for name in ("fake_en", "real_en"):
        assert card.card_data(mock_result(monkeypatch, name), "en")["note"] == ""
