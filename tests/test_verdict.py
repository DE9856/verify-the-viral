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


# the three real live calls (server, phone, 2026-11-26; research/live-listen.md)
O6YZ8A = [(1.31, 5.31, "real", .01), (3.31, 7.31, "fake", .66), (5.31, 9.31, "fake", .65), (7.31, 11.31, "fake", .71),
          (9.31, 13.31, "real", .04), (11.31, 15.31, "real", .05), (13.31, 17.31, "real", .08), (15.31, 22.99, "real", .57),
          (17.31, 24.99, "fake", .99), (22.99, 26.99, "fake", .98), (24.99, 28.99, "fake", .98), (26.99, 30.99, "fake", .97),
          (28.99, 32.99, "fake", 1.0), (30.99, 34.99, "fake", .98), (32.99, 41.92, "real", .39), (34.99, 43.92, "real", .20),
          (41.92, 45.92, "fake", .85), (43.92, 47.92, "fake", .65), (45.92, 49.92, "fake", .72), (47.92, 51.92, "fake", .73),
          (49.92, 53.92, "fake", .98), (51.92, 55.92, "fake", .95), (53.92, 57.92, "real", .05), (55.92, 59.92, "real", .01)]
DEZRG = [(0.86, 4.86, "real", .06), (2.86, 6.86, "fake", .97), (4.86, 8.86, "fake", .97), (6.86, 10.86, "real", .86),
         (8.86, 12.86, "real", .05), (10.86, 14.86, "real", .03), (12.86, 16.86, "real", .01), (13.41, 17.41, "real", .01)]
ZXOUDG = [(2.0 * i, 2.0 * i + 4, "real", .95 if i == 7 else .02) for i in range(10)]   # one 0.95 window labelled real


def _live(rows, verdict="real", score=0.1, speech=20.0):
    return {"verdict": verdict, "score": score, "scored_seconds": speech,
            "segments": [{"start": a, "end": b, "verdict": v, "score": s} for a, b, v, s in rows]}


def test_live_rule_on_the_three_real_calls():
    from app.core.verdict import decide_live
    assert decide_live(_live(ZXOUDG)) == {"band": "no_signs", "core_regions": []}         # real voice
    assert decide_live(_live(DEZRG, score=0.37)) == {"band": "unclear", "core_regions": []}   # 2 s burst at 0.97
    out = decide_live(_live(O6YZ8A, "fake", 0.57, 50.3))                                  # real + clone + spliced
    assert out == {"band": "partly_fake", "core_regions": [[22.99, 32.99]]}                 # the clone only
    assert decide(_live(DEZRG, score=0.37))["band"] == "partly_fake"                      # the file rule would cry wolf


def test_live_whole_call_clone_is_likely_fake():
    from app.core.verdict import decide_live
    rows = [(2.0 * i, 2.0 * i + 4, "fake", .98) for i in range(8)]
    assert decide_live(_live(rows, "fake", 0.96))["band"] == "likely_fake"
    assert decide_live(_live(rows, "fake", 0.60))["band"] == "partly_fake"   # unsure overall: show the seconds
