"""Lane A: AI-clip radar (store.radar, /radar, /api/radar). Fake Aletheia, no network, no credits."""
import asyncio
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app import api, config
from app.core import check as check_mod, store
from tests.test_cache import AUDIO, fake  # noqa: F401  (pytest fixture)


def run(path, chat_id, tg=None, channel="telegram"):
    source = {"channel": channel, "tg_file_unique_id": tg, "filename": Path(path).name}
    if chat_id is not None:
        source["chat_id"] = chat_id
    return asyncio.run(check_mod.check(str(path), source=source))


def test_flagged_clip_appears_once_seen_in_two_chats(fake):
    r = run(AUDIO / "spliced_en.wav", chat_id=-1001)
    assert store.radar()["items"] == []                      # checked once: private, not listed
    run(AUDIO / "spliced_en.wav", chat_id=-1002)             # forwarded to a second group (cache hit)
    items = store.radar()["items"]
    assert [i["id"] for i in items] == [r["id"]]
    assert items[0]["places"] == 2 and items[0]["times_checked"] == 2
    assert items[0]["core_regions"] == [[10.0, 14.0]] and items[0]["segments"]
    assert fake.calls == 1


def test_three_checks_in_one_chat_also_count(fake):
    for _ in range(3):
        run(AUDIO / "spliced_en.wav", chat_id=-1001)
    (item,) = store.radar()["items"]
    assert item["places"] == 1 and item["times_checked"] == 3


def test_share_app_counts_as_one_place(fake):
    run(AUDIO / "spliced_en.wav", chat_id=None, channel="share")
    run(AUDIO / "spliced_en.wav", chat_id=-1001)
    assert store.radar()["items"][0]["places"] == 2


def test_chat_ids_are_never_stored(fake):
    run(AUDIO / "spliced_en.wav", chat_id=-100987654321)
    con = sqlite3.connect(config.DB_PATH)
    dump = "\n".join(con.iterdump())
    assert "987654321" not in dump
    (place,) = con.execute("SELECT place FROM sightings").fetchone()
    assert place.startswith("tg:") and len(place) == 19


def test_clean_clips_and_mock_results_never_listed(fake, monkeypatch):
    fake.fixture = "real_en"
    for chat in (-1, -2, -3):
        run(AUDIO / "real_en.wav", chat_id=chat)
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "spliced_en")    # recorded result, no operation_id
    for chat in (-1, -2, -3):
        run(AUDIO / "spliced_en.wav", chat_id=chat)
    assert store.radar()["items"] == []


def test_stats_count_repeats_and_credits_saved(fake):
    for chat in (-1, -2, -3):
        run(AUDIO / "spliced_en.wav", chat_id=chat)
    st = store.radar()["stats"]
    (duration,) = sqlite3.connect(config.DB_PATH).execute("SELECT duration FROM checks").fetchone()
    per_check = max(store.MIN_CREDITS, round(store.CREDITS_PER_SECOND * duration))   # DetectifAI pricing
    assert st == {"clips": 1, "checks": 3, "repeats": 2, "credits_saved": 2 * per_check,
                  "edited_copies": 0, "credits_saved_on_edits": 0}


def test_radar_page_and_json(fake):
    for chat in (-1, -2):
        run(AUDIO / "spliced_en.wav", chat_id=chat)
    client = TestClient(api.app)
    page = client.get("/radar")
    assert page.status_code == 200 and "AI-clip radar" in page.text and "__I18N__" not in page.text
    assert "Partly AI-generated" in page.text                  # band labels embedded from i18n.json
    data = client.get("/api/radar")
    assert data.headers["cache-control"] == "no-store"
    body = data.json()
    assert set(body) == {"items", "stats", "rules"} and len(body["items"]) == 1
    assert body["rules"] == {"min_places": 2, "min_checks": 3, "days": 7}
