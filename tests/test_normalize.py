"""Lane A · A1: normalize() picks the cheapest valid path for each kind of upload."""
import subprocess
from pathlib import Path

import pytest

from app.core import normalize
from app.core.normalize import NormalizeError

FF = normalize.FFMPEG
ROOT = Path(__file__).resolve().parent.parent


def make(path: Path, *args: str) -> str:
    subprocess.run([FF, "-v", "error", "-y", *args, str(path)], check=True)
    return str(path)


def sine(seconds: float) -> list[str]:
    return ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]


def test_voice_note_is_sent_unchanged(tmp_path):
    src = make(tmp_path / "voice.ogg", *sine(6), "-c:a", "libopus", "-b:a", "24k")
    n = normalize.normalize_sync(src)
    assert n.method == "passthrough" and n.path.endswith(".ogg") and not n.trimmed
    assert Path(n.path).read_bytes() == Path(src).read_bytes()
    assert 5.9 < n.duration < 6.2


def test_recorded_test_clips_pass_through():
    for name in ("real_en.wav", "fake_kn.mp3", "spliced_whatsapp.ogg"):
        assert normalize.normalize_sync(str(ROOT / "research" / "test-audio" / name)).method == "passthrough"


def test_video_audio_is_stream_copied(tmp_path):
    src = make(tmp_path / "clip.mp4", "-f", "lavfi", "-i", "color=c=black:s=160x120:d=5", *sine(5),
               "-shortest", "-c:v", "libx264", "-c:a", "aac")
    n = normalize.normalize_sync(src)
    assert n.method == "copy" and n.path.endswith(".m4a")


def test_long_audio_is_trimmed_to_300s(tmp_path):
    src = make(tmp_path / "long.ogg", *sine(310), "-c:a", "libopus", "-b:a", "16k")
    n = normalize.normalize_sync(src)
    assert n.trimmed and n.method == "copy" and n.duration == 300
    assert normalize.probe(n.path).duration <= 300.1


def test_unusual_codec_is_transcoded(tmp_path):
    src = make(tmp_path / "odd.avi", *sine(5), "-c:a", "pcm_s16le")
    n = normalize.normalize_sync(src)
    assert n.method == "transcode" and n.path.endswith(".ogg")
    assert normalize.probe(n.path).audio_codec == "opus"


def test_video_without_audio_is_rejected(tmp_path):
    src = make(tmp_path / "silent.mp4", "-f", "lavfi", "-i", "color=c=black:s=160x120:d=3", "-c:v", "libx264")
    with pytest.raises(NormalizeError) as e:
        normalize.normalize_sync(src)
    assert e.value.code == "no_audio"


def test_garbage_is_rejected(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("not audio")
    with pytest.raises(NormalizeError) as e:
        normalize.normalize_sync(str(src))
    assert e.value.code == "unreadable"


def test_same_content_is_stored_once(tmp_path):
    src = make(tmp_path / "a.ogg", *sine(5), "-c:a", "libopus")
    copy = tmp_path / "b.ogg"
    copy.write_bytes(Path(src).read_bytes())
    a, b = normalize.normalize_sync(src), normalize.normalize_sync(str(copy))
    assert a.sha256 == b.sha256 and a.path == b.path
