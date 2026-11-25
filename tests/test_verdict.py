"""Lane A · A2 "done when": verdict.decide() gives the expected band for every recorded result.
Skipped until decide() is implemented."""
import json

import pytest

from app import config
from app.core import verdict

EXPECTED = json.loads((config.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))


def load(name):
    return json.loads((config.FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))["result"]


def decide_or_skip(result):
    try:
        return verdict.decide(result)
    except NotImplementedError:
        pytest.skip("Lane A · A2 not done yet")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_recorded_results(name):
    out = decide_or_skip(load(name))
    assert out["band"] == EXPECTED[name]["band"]
    assert [[round(a, 1), round(b, 1)] for a, b in out["core_regions"]] == EXPECTED[name]["core_regions"]


def test_missing_verdict_falls_back_to_label():
    r = load("fake_en"); r.pop("verdict", None)
    assert decide_or_skip(r)["band"] == "likely_fake"


def test_short_clip_is_unclear():
    r = load("real_en"); r["scored_seconds"] = 6.0
    assert decide_or_skip(r)["band"] == "unclear"


def test_single_isolated_fake_window_is_unclear():
    r = load("real_en")
    r["segments"][4] = {**r["segments"][4], "score": 0.9, "verdict": "fake"}  # 8–12 s only
    assert decide_or_skip(r)["band"] == "unclear"
