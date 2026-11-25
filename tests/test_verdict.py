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
from app.core.verdict import apply_edits, decide  # noqa: E402

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


def test_live_score_floor_on_the_phone_run():
    """Phone test o6yz8A (server, 2026-11-26): real speech through a speaker came back fake at 0.65-0.85.
    With min_score 0.9 only the clone and the AI sentence are marked (truth in stream time: clone
    21.4-35.7, AI sentence 49.7-53.5), and the 0.57 overall 'fake' no longer decides alone."""
    T = [(1.31, 5.31, "real", .01), (3.31, 7.31, "fake", .66), (5.31, 9.31, "fake", .65), (7.31, 11.31, "fake", .71),
         (9.31, 13.31, "real", .04), (11.31, 15.31, "real", .05), (13.31, 17.31, "real", .08), (15.31, 22.99, "real", .57),
         (17.31, 24.99, "fake", .99), (22.99, 26.99, "fake", .98), (24.99, 28.99, "fake", .98), (26.99, 30.99, "fake", .97),
         (28.99, 32.99, "fake", 1.0), (30.99, 34.99, "fake", .98), (32.99, 41.92, "real", .39), (34.99, 43.92, "real", .20),
         (41.92, 45.92, "fake", .85), (43.92, 47.92, "fake", .65), (45.92, 49.92, "fake", .72), (47.92, 51.92, "fake", .73),
         (49.92, 53.92, "fake", .98), (51.92, 55.92, "fake", .95), (53.92, 57.92, "real", .05), (55.92, 59.92, "real", .01)]
    r = {"verdict": "fake", "score": 0.57, "scored_seconds": 50.3,
         "segments": [{"start": a, "end": b, "verdict": v, "score": s} for a, b, v, s in T]}
    assert decide(r)["band"] == "likely_fake"                                   # the file-check rule
    assert decide(r, min_score=0.9) == {"band": "partly_fake", "core_regions": [[22.99, 32.99], [51.92, 53.92]]}


def test_live_weak_fakes_alone_make_it_unclear_not_green():
    segs = [{"start": 0, "end": 4, "verdict": "fake", "score": 0.7}, {"start": 2, "end": 6, "verdict": "fake", "score": 0.66}]
    r = {"verdict": "real", "score": 0.2, "scored_seconds": 20, "segments": segs}
    assert decide(r)["band"] == "partly_fake" and decide(r, min_score=0.9)["band"] == "unclear"
