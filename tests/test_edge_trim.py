"""Edge silence is cut from the copy we send (billed seconds), never from what we store or show."""
import subprocess

import numpy as np

from app.core import normalize
from app.core.normalize import FFMPEG
from tests.test_cache import AUDIO, fake, run  # noqa: F401  (fake = fixture)


def _pad(src, dst, lead, tail):
    g = (f"[0:a]aformat=sample_rates=16000:channel_layouts=mono[a];"
         f"[a]adelay={int(lead * 1000)},apad=pad_dur={tail}[o]")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-filter_complex", g, "-map", "[o]",
                    "-c:a", "libopus", "-b:a", "24k", str(dst)], check=True)
    return dst


def test_plan_only_trims_when_it_saves_credits():
    speech = (np.random.default_rng(0).normal(0, 0.2, 16000 * 12) * 32767).astype(np.int16)
    quiet = np.zeros(16000 * 3, np.int16)
    padded = np.concatenate([quiet, speech, quiet]).tobytes()
    start, length = normalize.trim_plan(padded, 18.0)
    assert start == 2.0 and abs(length - 13.3) < 0.1                       # 2 s steps at the start
    assert normalize.trim_plan(speech.tobytes(), 12.0) is None                         # nothing to cut
    assert normalize.trim_plan(np.concatenate([quiet, speech[:16000 * 8]]).tobytes(), 11.0) is None  # < 10.5 s left


def test_padded_clip_sends_less_but_keeps_original_times(fake, tmp_path):
    a = run(AUDIO / "spliced_en.wav")                           # fixture: fake part 10-14 s
    clip = _pad(AUDIO / "real_en.wav", tmp_path / "padded.ogg", 3.0, 3.0)
    norm = normalize.normalize_sync(str(clip))
    assert norm.send_path and norm.offset == 2.0
    assert normalize.probe(norm.send_path).duration < norm.duration - 4.0
    assert normalize.probe(norm.path).duration > norm.duration - 0.2          # stored file stays whole
    b = run(clip)
    assert b["duration"] == norm.duration
    (lo, hi), = b["core_regions"]                                            # times moved to the original's
    assert abs(lo - (10.0 + norm.offset)) < 0.01 and abs(hi - (14.0 + norm.offset)) < 0.01
    assert a["core_regions"] == [[10.0, 14.0]]


def test_clip_without_edge_silence_is_sent_unchanged(fake):
    norm = normalize.normalize_sync(str(AUDIO / "spliced_whatsapp.ogg"))
    assert norm.send_path is None and norm.method == "passthrough"
