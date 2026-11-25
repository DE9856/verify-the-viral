"""Lane A: the flagged seconds as a playable clip (app/core/excerpt.py). Mock mode, no credits."""
import asyncio

from app import config
from app.core import check as check_mod, excerpt, normalize


def mock_result(monkeypatch, name):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", name)
    return asyncio.run(check_mod.check("x.ogg", source={"channel": "telegram",
                                                        "tg_file_unique_id": None, "filename": "x.ogg"}))


def test_partly_fake_clip_is_exactly_the_flagged_seconds(monkeypatch):
    result = mock_result(monkeypatch, "spliced_en")
    path, region = asyncio.run(excerpt.fake_part(result))
    assert region == [10.0, 14.0]
    p = normalize.probe(path)
    assert p.audio_codec == "opus" and p.demuxer == "ogg"     # Telegram plays it as a voice note
    assert abs(p.duration - 4.0) < 0.1
    again, _ = asyncio.run(excerpt.fake_part(result))
    assert again == path                                      # cached, not cut twice


def test_no_clip_unless_partly_fake(monkeypatch):
    for name in ("fake_en", "real_en"):
        assert asyncio.run(excerpt.fake_part(mock_result(monkeypatch, name))) is None


def test_no_clip_without_stored_audio():
    result = {"id": "nope", "band": "partly_fake", "core_regions": [[1.0, 5.0]]}
    assert asyncio.run(excerpt.fake_part(result)) is None


def test_longest_region_wins_and_long_ones_are_capped():
    assert excerpt.pick_region([[2, 6], [10, 18], [20, 28]]) == [10, 18]   # tie → earliest
    assert excerpt.pick_region([]) is None
    assert excerpt.MAX_SECONDS == 30.0
