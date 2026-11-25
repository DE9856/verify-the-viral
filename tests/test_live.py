"""Live listen (app/core/live.py, WS /ws/live): the relay, the mock stream, storing the final result.
No network, no credits: the mock stream, or a fake that sends the messages the DetectifAI docs show."""
import json
import wave

import pytest
from fastapi.testclient import TestClient

from app import api, config
from app.core import live, store

FRAME = b"\x00\x00" * 1600          # 0.1 s of 16 kHz 16-bit silence


@pytest.fixture
def client():
    with TestClient(api.app) as c:
        yield c


def _send_seconds(ws, seconds):
    for _ in range(int(seconds * 10)):
        ws.send_bytes(FRAME)


def _until(ws, kind):
    seen = []
    while True:
        m = ws.receive_json()
        seen.append(m)
        if m["type"] in (kind, "error"):
            return m, seen


def test_mock_stream_live_updates_then_a_stored_result(client, monkeypatch):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "cycle")
    with client.websocket_connect("/ws/live") as ws:
        assert ws.receive_json()["type"] == "ready"
        _send_seconds(ws, 22)
        ws.send_text(json.dumps({"type": "stop"}))
        result, seen = _until(ws, "result")
    updates = [m for m in seen if m["type"] == "update"]
    assert updates[0]["early"] and updates[0]["verdict"] == "real"          # 0-6 s: before the fake part
    assert any(m["verdict"] == "fake" for m in updates)                     # the recorded fake part at 8-16 s
    assert result["band"] == "partly_fake" and result["result_url"] == f"/r/{result['id']}"
    stored = store.get(result["id"])
    assert stored["live"]["speech_seconds"] == pytest.approx(22, abs=0.2) and stored["credits_charged"] == 0
    with wave.open(store.audio_path(result["id"])) as w:                    # audio kept for the result page
        assert w.getframerate() == 16000 and w.getnframes() == 22 * 16000


def test_too_little_speech_is_an_error_and_keeps_nothing(client, monkeypatch):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "cycle")
    with client.websocket_connect("/ws/live") as ws:
        ws.receive_json()
        _send_seconds(ws, 1)
        ws.send_text(json.dumps({"type": "stop"}))
        m, _ = _until(ws, "result")
    assert m == {"type": "error", "code": "insufficient_speech"}
    assert not list((config.DB_PATH.parent / "audio").glob("live_*.wav"))


class DocsStream:
    """Sends the messages the live-call-streams docs show, to test the real-stream path."""

    def __init__(self, close_code=None, completed=True):
        self.frames, self.stopped, self.close_code, self.completed = 0, False, close_code, completed
        self.out = [{"type": "ready", "stream_id": "str_1", "reference": "x", "checks": ["deepfake"]}]

    async def send_audio(self, frame):
        self.frames += 1
        if self.frames == 60:
            self.out.append({"type": "deepfake", "early": True, "final": False, "sequence": 1, "seconds": 6.0,
                             "speech_seconds": 4.5, "window_seconds": 4.5, "verdict": "real", "score": 0.012})

    async def send_stop(self):
        self.stopped = True

    async def recv(self):
        import asyncio
        while not self.out:
            if self.stopped:
                if not self.completed:
                    return None
                self.completed = False
                return {"type": "completed", "status": "completed", "seconds": 12.0, "speech_seconds": 11.0,
                        "ended_by": "client_stop", "results": {"deepfake": {
                            "object": "deepfake.detection", "operation_id": "op_6f1e", "final": True, "updates": 1,
                            "result": {"verdict": "real", "score": 0.046, "duration_seconds": 12.0, "scored_seconds": 11.0,
                                       "segments": [{"start": 0.0, "end": 4.0, "score": 0.01, "verdict": "real"},
                                                    {"start": 2.0, "end": 6.0, "score": 0.97, "verdict": "fake"},
                                                    {"start": 4.0, "end": 8.0, "score": 0.98, "verdict": "fake"},
                                                    {"start": 6.0, "end": 10.0, "score": 0.02, "verdict": "real"}]}}}}
            await asyncio.sleep(0.01)
        return self.out.pop(0)

    async def close(self):
        pass


def test_real_stream_messages_become_a_normal_check(client, monkeypatch):
    stream = DocsStream()

    async def opener(ref):
        return stream
    monkeypatch.setattr(live, "open_stream", opener)
    with client.websocket_connect("/ws/live") as ws:
        ws.receive_json()
        _send_seconds(ws, 12)
        ws.send_text(json.dumps({"type": "stop"}))
        result, seen = _until(ws, "result")
    assert [m for m in seen if m["type"] == "update"][0]["verdict"] == "real"
    assert result["band"] == "partly_fake" and result["core_regions"] == [[4.0, 6.0]]
    r = store.get(result["id"])
    assert r["operation_id"] == "op_6f1e" and r["credits_charged"] == 22       # 11 s of speech x 2


def test_stream_closed_for_credits_says_so(client, monkeypatch):
    stream = DocsStream(close_code=4402, completed=False)

    async def opener(ref):
        return stream
    monkeypatch.setattr(live, "open_stream", opener)
    with client.websocket_connect("/ws/live") as ws:
        ws.receive_json()
        _send_seconds(ws, 2)
        ws.send_text(json.dumps({"type": "stop"}))
        m, _ = _until(ws, "result")
    assert m == {"type": "error", "code": "out_of_credits"}


def test_live_checks_never_reach_the_radar():
    done = {"seconds": 30, "speech_seconds": 30, "ended_by": "client_stop"}
    res = {"operation_id": "op_live", "result": {"verdict": "fake", "score": 0.9, "duration_seconds": 30,
                                                 "scored_seconds": 30, "segments": []}}
    r = live.save_result("liveid", done, res, "x.wav")
    for _ in range(3):
        store.hit(r["id"], source={"channel": "live"})
    assert r["band"] == "likely_fake" and store.radar()["items"] == []


def test_live_page_renders_in_kannada(client):
    html = client.get("/live?lang=kn").text
    assert "ಲೈವ್ ಆಲಿಸಿ" in html and "__I18N__" not in html and "MOCK = false" in html
