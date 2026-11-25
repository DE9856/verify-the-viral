"""Lane B: bot reply wording on every mock fixture (no Telegram connection needed)."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app import bot, config
from app.core import check as check_mod

EXPECTED = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))


def mock_result(monkeypatch, name):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", name)
    return asyncio.run(check_mod.check("x.ogg", source={"channel": "telegram",
                                                        "tg_file_unique_id": None, "filename": "x.ogg"}))


@pytest.mark.parametrize("lang", ["en", "hi", "kn"])
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_reply_for_every_fixture(monkeypatch, name, lang):
    text = bot.format_reply(mock_result(monkeypatch, name), lang)
    assert text and "{" not in text
    assert text.startswith({"likely_fake": "🔴", "partly_fake": "🟠", "no_signs": "🟢"}[EXPECTED[name]["band"]])


def test_partly_fake_names_the_seconds(monkeypatch):
    assert "10–14 s" in bot.format_reply(mock_result(monkeypatch, "spliced_en"), "en")


def test_error_replies(monkeypatch):
    r = mock_result(monkeypatch, "error_insufficient_speech")
    assert bot.format_reply(r, "en") == bot.t("error_insufficient_speech", "en")
    r["error"]["code"] = "something_new"
    assert bot.format_reply(r, "en") == bot.t("error_failed", "en")


def test_pick_media_order():
    msg = SimpleNamespace(voice=None, audio=None, video="v", video_note=None, document=None)
    assert bot.pick_media(msg) == ("video", "v")
    assert bot.pick_media(SimpleNamespace(voice=None, audio=None, video=None, video_note=None,
                                          document=None)) == (None, None)


def test_mock_replies_say_test_mode(monkeypatch):
    note = bot.t("mock_note", "kn")
    assert note in bot.format_reply(mock_result(monkeypatch, "real_en"), "kn")
    r = mock_result(monkeypatch, "real_en")
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "")
    assert note not in bot.format_reply(r, "kn")


def test_regions_use_local_seconds(monkeypatch):
    assert "10–14 ಸೆಕೆಂಡು" in bot.format_reply(mock_result(monkeypatch, "spliced_en"), "kn")
    assert "10–14 सेकंड" in bot.format_reply(mock_result(monkeypatch, "spliced_en"), "hi")


def test_chat_language_default_set_and_saved(monkeypatch, tmp_path):
    monkeypatch.setattr(bot, "LANG_FILE", tmp_path / "langs.json")
    monkeypatch.setattr(bot, "_chat_langs", {})
    assert bot.chat_lang(-100) == config.DEFAULT_LANG
    bot.set_chat_lang(-100, "hi")
    assert bot.chat_lang(-100) == "hi" and bot.chat_lang(-200) == config.DEFAULT_LANG
    assert bot._load_langs() == {"-100": "hi"}


def test_every_bot_key_in_every_language():
    for key in ["seconds", "mock_note", "start", "lang_set", "lang_usage", "lang_admins_only", "trimmed"]:
        assert all(bot.I18N[key].get(lang) for lang in bot.LANGS), key
