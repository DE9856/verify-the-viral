"""Edited copies pay only for their new seconds (app/core/edits.py). Fake Aletheia, 0 credits."""
import json
import subprocess

import httpx

from app.core import edits
from app.core.normalize import FFMPEG
from tests.test_cache import AUDIO, FIX, _replace, fake, needs_fpcalc, run  # noqa: F401  (fake = fixture)

ORIGINAL = {"band": "partly_fake", "core_regions": [[10.0, 14.0]], "duration": 20.4,
            "segments": [{"start": s, "end": s + 4.0, "score": 0.9 if 8 <= s <= 12 else 0.01,
                          "verdict": "fake" if 8 <= s <= 12 else "real"} for s in range(0, 17, 2)]}


def test_plan_picks_the_cheapest_safe_mode():
    assert edits.plan({**ORIGINAL, "band": "likely_fake"}, [[2, 4]], [], 20.4).mode == "free"
    c = edits.plan(ORIGINAL, [], [[16.0, 19.0]], 17.4)                         # a cut: checked around it
    assert c.mode == "excerpt" and c.cut and c.start <= 16.0 <= c.end
    p = edits.plan(ORIGINAL, [[16.6, 19.2]], [], 22.4)
    assert p.mode == "excerpt" and abs((p.end - p.start) - edits.EXCERPT_SECONDS) < 0.05
    assert p.start <= 16.6 and p.end >= 19.2 and p.shift == 2.0
    assert edits.plan(ORIGINAL, [[2, 4], [15, 17]], [], 20.4).mode == "full"       # two changes
    assert edits.plan(ORIGINAL, [[6.9, 10.3]], [[7.1, 10.2]], 20.4).mode == "excerpt"  # replaced in place
    assert edits.plan(ORIGINAL, [[2.0, 4.0]], [[15.0, 17.0]], 20.4).mode == "full"     # change + a cut elsewhere
    assert edits.plan(ORIGINAL, [[1, 9]], [], 12.0).mode == "full"                 # excerpt ~ whole clip
    assert edits.plan({**ORIGINAL, "band": "error"}, [], [[3, 5]], 18.0).mode == "full"


def test_messy_diff_gets_the_whole_clip_checked():
    """Unmatched seconds the reported changes don't explain may be an edit too small to report."""
    assert edits.plan(ORIGINAL, [[16.6, 19.2]], [], 22.4, typical=0.994, stray=0.0).mode == "excerpt"
    assert edits.plan(ORIGINAL, [[16.6, 19.2]], [], 22.4, typical=0.994, stray=0.5).mode == "full"
    assert edits.plan(ORIGINAL, [[16.6, 19.2]], [], 22.4, typical=0.85, stray=0.0).mode == "full"
    red = {**ORIGINAL, "band": "likely_fake"}
    assert edits.plan(red, [[2, 4]], [], 20.4, typical=1.0, stray=0.0).mode == "free"
    assert edits.plan(red, [[2, 4]], [], 20.4, typical=1.0, stray=0.6).mode == "full"   # a false 🔴 gets a 2nd chance


def test_cut_moves_later_times_back():
    assert edits.map_cut(5.0, [[16.0, 19.0]]) == 5.0
    assert edits.map_cut(20.0, [[16.0, 19.0]]) == 17.0
    assert edits.map_cut(17.0, [[16.0, 19.0]]) == 16.0


def test_cut_excerpt_merges_and_is_never_green():
    p = edits.plan(ORIGINAL, [], [[2.0, 4.0]], 18.4)
    clean = {"threshold": 0.62, "segments": [{"start": 0.0, "end": 4.0, "score": 0.01, "verdict": "real"}]}
    m = edits.merge_excerpt(ORIGINAL, p, clean, [], [[2.0, 4.0]])
    assert [8.0, 12.0] in m["core_regions"] or m["core_regions"][-1][1] == 12.0    # original 10-14, moved 2 s back
    m = edits.merge_excerpt({**ORIGINAL, "band": "no_signs", "core_regions": []}, p, clean, [], [[2.0, 4.0]])
    assert m["band"] == "unclear" and m["reason"] == "edited"


def test_excerpt_merges_with_the_original():
    p = edits.plan(ORIGINAL, [[16.6, 19.2]], [], 22.4)
    flagged = {"threshold": 0.62, "segments": [{"start": s, "end": s + 4.0, "score": 0.95, "verdict": "fake"}
                                               for s in (2.0, 4.0, 6.0)]}
    m = edits.merge_excerpt(ORIGINAL, p, flagged, [[16.6, 19.2]])
    assert m["band"] == "partly_fake"
    assert m["core_regions"][0][0] == 10.0                                 # the original's fake part
    assert any(a >= p.start and b <= p.end for a, b in m["core_regions"] if a > 14)  # the new one
    clean = {"threshold": 0.62, "segments": [{"start": 0.0, "end": 4.0, "score": 0.01, "verdict": "real"}]}
    m = edits.merge_excerpt({**ORIGINAL, "band": "no_signs", "core_regions": []}, p, clean, [[16.6, 19.2]])
    assert m["band"] == "unclear" and m["reason"] == "edited"             # an edit is never green


def _cut(src, dst, a, b):
    g = (f"[0:a]atrim=0:{a},asetpts=N/SR/TB[x];[0:a]atrim={b},asetpts=N/SR/TB[y];[x][y]concat=n=2:v=0:a=1[o]")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-filter_complex", g, "-map", "[o]",
                    "-c:a", "libopus", "-b:a", "24k", str(dst)], check=True)
    return dst


@needs_fpcalc
def test_cut_copy_is_checked_around_the_cut(fake, tmp_path):
    a = run(AUDIO / "spliced_whatsapp.mp3")
    b = run(_cut(AUDIO / "spliced_whatsapp.mp3", tmp_path / "cut.ogg", 16.0, 19.0))
    e = b["edited_copy_of"]
    assert fake.calls == 2 and e["mode"] == "excerpt" and e["id"] == a["id"] and b["id"] != a["id"]
    lo, hi = e["rechecked"]
    assert lo <= 16.0 <= hi and abs((hi - lo) - edits.EXCERPT_SECONDS) < 0.05
    assert [10.0, 14.0] in b["core_regions"] or b["core_regions"][0][0] == 10.0     # the fake part is before the cut


@needs_fpcalc
def test_replaced_seconds_are_checked_as_a_short_excerpt(fake, tmp_path):
    sizes = []
    inner = fake.__call__

    def spy(request: httpx.Request):
        if request.url.path.endswith("/detect"):
            sizes.append(len(request.content))
        return inner(request)
    from app.core import aletheia
    aletheia.use_transport(httpx.MockTransport(spy))
    fake.fixture = "real_en"
    run(AUDIO / "real_en.wav")
    b = run(_replace(AUDIO / "real_en.wav", AUDIO / "fake_en.mp3", tmp_path, 8.0, 3))
    e = b["edited_copy_of"]
    assert fake.calls == 2 and e["mode"] == "excerpt"
    lo, hi = e["rechecked"]
    assert abs((hi - lo) - edits.EXCERPT_SECONDS) < 0.05 and lo <= 8.0 and hi >= 11.0
    assert sizes[1] < 16000 * 2 * 11 + 1000                 # ~10 s of 16 kHz WAV, not the whole clip
    assert b["band"] == "unclear" and b["reason"] == "edited"


@needs_fpcalc
def test_edited_copy_of_a_fake_clip_is_free(fake, tmp_path):
    fake.fixture = "fake_en"
    a = run(AUDIO / "fake_en.mp3")
    assert a["band"] == "likely_fake"
    b = run(_cut(AUDIO / "fake_en.mp3", tmp_path / "fake_cut.ogg", 3.0, 5.5))
    if b.get("edited_copy_of", {}).get("mode") == "free":   # only if the diff calls it a clean edit
        assert fake.calls == 1 and b["band"] == "likely_fake" and b["credits_charged"] == 0
        from app.core import store
        st = store.radar()["stats"]
        assert st["edited_copies"] == 1 and st["credits_saved_on_edits"] == max(20, round(2 * b["duration"]))
        assert st["credits_saved"] >= st["credits_saved_on_edits"]
