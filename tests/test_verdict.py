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


# --------------------------------------------------------------------------- apply_edits (fingerprint diff)
from app.core.verdict import apply_edits  # noqa: E402

SEG = lambda a, b, v: {"start": a, "end": b, "score": 0.9 if v == "fake" else 0.1, "verdict": v}  # noqa: E731


def test_unexplained_edit_never_stays_green():
    out = apply_edits({"band": "no_signs", "core_regions": []}, [SEG(0, 4, "real")], [[6.0, 8.0]], [])
    assert out == {"band": "unclear", "core_regions": [], "reason": "edited"}


def test_a_cut_alone_makes_it_unclear():
    out = apply_edits({"band": "no_signs", "core_regions": []}, [], [], [[3.0, 5.0]])
    assert out["band"] == "unclear" and out["reason"] == "edited"


def test_edit_backed_by_one_fake_window_becomes_an_ai_region():
    """One fake window alone isn't enough (decide() needs 2); the diff agreeing makes it a region."""
    segs = [SEG(0, 4, "fake"), SEG(2, 6, "real"), SEG(8, 12, "fake"), SEG(10, 14, "fake")]
    out = apply_edits({"band": "partly_fake", "core_regions": [[10.0, 12.0]]}, segs, [[1.24, 4.58]], [])
    assert out["band"] == "partly_fake" and out["core_regions"] == [[1.2, 4.6], [10.0, 12.0]]
    assert "reason" not in out


def test_edit_backed_by_a_window_turns_no_signs_into_partly_fake():
    out = apply_edits({"band": "no_signs", "core_regions": []}, [SEG(16, 20, "fake")], [[16.6, 19.2]], [])
    assert out["band"] == "partly_fake" and out["core_regions"] == [[16.6, 19.2]]


def test_flagged_bands_keep_their_colour():
    assert apply_edits({"band": "likely_fake", "core_regions": []}, [], [[1, 3]], [[5, 6]])["band"] == "likely_fake"
    out = apply_edits({"band": "partly_fake", "core_regions": [[10.0, 14.0]]}, [], [[11.0, 13.0], [18.0, 20.0]], [])
    assert out == {"band": "partly_fake", "core_regions": [[10.0, 14.0]]}   # edit inside a region / unexplained
