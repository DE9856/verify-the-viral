"""Lane A · A1–A3 end to end with a fake Aletheia (httpx.MockTransport): API calls, retries,
error mapping, the three cache tiers and single-flight. No network, no credits."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app import config
from app.core import aletheia, check as check_mod, fingerprint, store

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "research" / "test-audio"
FIX = ROOT / "app" / "fixtures"


class FakeAletheia:
    """Answers /v1/deepfake/detect with a recorded fixture; can be told to fail first."""

    def __init__(self, fixture="spliced_en", fail_with=None, fail_times=0):
        self.calls, self.keys, self.feedback = 0, [], []
        self.fixture, self.fail_with, self.fail_times = fixture, fail_with, fail_times

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/health":
            return httpx.Response(200, json={"status": "ok", "inference": "ok"})
        if request.url.path.endswith("/feedback"):
            self.feedback.append(json.loads(request.content))
            return httpx.Response(200, json={"object": "operation.feedback"})
        assert request.headers["authorization"] == "Bearer test-key"
        self.calls += 1
        self.keys.append(request.headers.get("idempotency-key"))
        if self.calls <= self.fail_times:
            status, code = self.fail_with
            return httpx.Response(status, headers={"retry-after": "0"},
                                  json={"error": {"code": code, "message": f"fake {code}"}})
        raw = json.loads((FIX / f"{self.fixture}.json").read_text(encoding="utf-8"))
        raw["credits"] = {"charged": 50, "balance": 4950}
        return httpx.Response(200, json=raw)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "")
    monkeypatch.setattr(config, "DETECTIF_API_KEY", "test-key")
    f = FakeAletheia()
    aletheia.use_transport(httpx.MockTransport(f))
    yield f
    aletheia.use_transport(None)


def run(path, tg=None):
    return asyncio.run(check_mod.check(str(path), source={"channel": "telegram", "tg_file_unique_id": tg,
                                                          "filename": Path(path).name}))


def test_first_check_calls_api_and_stores(fake):
    r = run(AUDIO / "spliced_en.wav")
    assert r["band"] == "partly_fake" and r["core_regions"] == [[10.0, 14.0]]
    assert r["credits_charged"] == 50 and r["cache"] == {"hit": False, "times_checked": 1}
    assert fake.calls == 1 and len(fake.keys[0]) == 64          # sha256 as Idempotency-Key
    assert store.get(r["id"])["band"] == "partly_fake"
    assert r["result_url"] == f"https://example.test/r/{r['id']}"


def test_same_file_again_is_free(fake):
    a = run(AUDIO / "spliced_en.wav")
    b = run(AUDIO / "spliced_en.wav")
    assert fake.calls == 1 and b["id"] == a["id"]
    assert b["cache"] == {"hit": True, "times_checked": 2} and b["credits_charged"] == 0


@pytest.mark.skipif(fingerprint.fpcalc_path() is None, reason="fpcalc not installed")
def test_whatsapp_reencode_hits_fingerprint_cache(fake):
    a = run(AUDIO / "spliced_en.wav")
    b = run(AUDIO / "spliced_whatsapp.ogg")                       # different bytes, same speech
    assert fake.calls == 1 and b["id"] == a["id"] and b["cache"]["hit"]


def test_telegram_id_hit_skips_all_work(fake):
    a = run(AUDIO / "spliced_en.wav", tg="AgADtg1")
    b = run(AUDIO / "does-not-exist.ogg", tg="AgADtg1")             # never opened
    assert fake.calls == 1 and b["id"] == a["id"] and b["cache"]["times_checked"] == 2


def test_different_clip_is_checked(fake):
    run(AUDIO / "spliced_en.wav")
    fake.fixture = "fake_en"
    r = run(AUDIO / "fake_en.mp3")
    assert fake.calls == 2 and r["band"] == "likely_fake"


def test_simultaneous_identical_clips_share_one_call(fake):
    async def both():
        src = {"channel": "telegram", "tg_file_unique_id": None, "filename": "x"}
        return await asyncio.gather(check_mod.check(str(AUDIO / "real_en.wav"), source=src),
                                    check_mod.check(str(AUDIO / "real_en.wav"), source=src))
    fake.fixture = "real_en"
    a, b = asyncio.run(both())
    assert fake.calls == 1 and a["id"] == b["id"], (a["band"], a["error"], a["cache"], b["band"], b["error"], b["cache"])
    assert sorted([a["cache"]["hit"], b["cache"]["hit"]]) == [False, True]


def test_rate_limit_is_retried_with_same_key(fake):
    fake.fail_with, fake.fail_times = (429, "rate_limited"), 2
    r = run(AUDIO / "spliced_en.wav")
    assert r["band"] == "partly_fake" and fake.calls == 3 and len(set(fake.keys)) == 1


@pytest.mark.parametrize("status,code,expected", [
    (422, "insufficient_speech", "insufficient_speech"),
    (402, "insufficient_credits", "out_of_credits"),
    (415, "unsupported_format", "failed"),
])
def test_api_errors_map_to_contract_codes(fake, status, code, expected):
    fake.fail_with, fake.fail_times = (status, code), 99
    r = run(AUDIO / "spliced_en.wav")
    assert r["band"] == "error" and r["error"]["code"] == expected and fake.calls == 1
    assert store.get(r["id"])["band"] == "error"
    assert run(AUDIO / "spliced_en.wav")["band"] == "error"       # errors are never served from cache
    assert fake.calls == 2


def test_missing_key_is_a_clean_error(fake, monkeypatch):
    monkeypatch.setattr(config, "DETECTIF_API_KEY", "")
    r = run(AUDIO / "spliced_en.wav")
    assert r["band"] == "error" and r["error"]["code"] == "failed" and fake.calls == 0


def test_feedback_is_stored_and_forwarded(fake):
    r = run(AUDIO / "spliced_en.wav")
    asyncio.run(check_mod.send_feedback(r["operation_id"], False, "real"))
    assert fake.feedback == [{"correct": False, "label": "real"}]
    assert store.stats()["feedback"] == 1


def test_mock_mode_results_are_stored(monkeypatch):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "spliced_en")
    r = run("anything.ogg")
    assert store.get(r["id"])["band"] == "partly_fake"
    assert store.audio_path(r["id"]).endswith("spliced_en.wav")
