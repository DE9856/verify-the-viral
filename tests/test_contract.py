"""Shared: the mock check() must always honour CONTRACT.md. Keep this green on every commit."""
import asyncio
import json

import pytest

from app import config
from app.core import check as check_mod

KEYS = {"id", "operation_id", "model", "band", "overall", "core_regions", "segments", "duration",
        "scored_seconds", "trimmed", "cache", "credits_charged", "error", "result_url"}
BANDS = {"likely_fake", "partly_fake", "unclear", "no_signs", "error"}
EXPECTED = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))


def run_mock(monkeypatch, name):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", name)
    return asyncio.run(check_mod.check("unused.ogg", source={"channel": "telegram",
                                                             "tg_file_unique_id": None, "filename": "x.ogg"}))


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_mock_fixture_matches_contract(monkeypatch, name):
    r = run_mock(monkeypatch, name)
    assert set(r) == KEYS
    assert r["band"] in BANDS and r["band"] == EXPECTED[name]["band"]
    assert r["core_regions"] == EXPECTED[name]["core_regions"]
    assert r["overall"]["verdict"] in {"real", "fake"}
    assert r["segments"] and all({"start", "end", "score", "verdict"} <= set(s) for s in r["segments"])
    assert r["credits_charged"] == 0 and r["error"] is None
    assert r["result_url"].endswith("/r/" + r["id"])


def test_mock_error(monkeypatch):
    r = run_mock(monkeypatch, "error_insufficient_speech")
    assert set(r) == KEYS and r["band"] == "error" and r["error"]["code"] == "insufficient_speech"


def test_cycle_covers_every_band(monkeypatch):
    bands = {run_mock(monkeypatch, "cycle")["band"] for _ in range(len(check_mod.MOCK_NAMES))}
    assert bands == {"likely_fake", "partly_fake", "no_signs"}


def test_i18n_has_every_key_in_every_language():
    i18n = json.loads(config.I18N_PATH.read_text(encoding="utf-8"))
    needed = BANDS - {"error"} | {"error_insufficient_speech", "error_too_large", "error_out_of_credits",
                                  "error_failed", "cache_hit", "disclaimer", "view_timeline",
                                  "feedback_question", "feedback_thanks"}
    for key in needed:
        assert {"en", "hi", "kn"} <= set(i18n[key]), key
