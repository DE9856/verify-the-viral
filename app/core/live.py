"""Live listen: check a voice while it is being heard (a call on speakerphone, a live speech).

    browser /live page ──mic, 16 kHz PCM, ~0.1 s frames──► WS /ws/live (this module)
          ▲                                                   │ keeps a WAV copy
          │                                                   ▼
          └── live updates ◄── Aletheia live stream  wss://platform.detectif.ai/v1/stream?checks=deepfake

Why a relay and not the browser straight to DetectifAI: the API key must never reach the page, and
the docs don't cover browsers (no CORS/origin notes; their clients send an Authorization header,
which a browser WebSocket can't). So our server opens the stream with the header.

Aletheia sends an early verdict after the first 4.5-8 s of speech, then one every
LIVE_UPDATE_SECONDS of new speech, each covering the last `window_seconds`. On stop it sends
`completed` with a final result for the whole call, segments included: that goes through the usual
verdict rules and is stored as a normal check (channel "live", never on the radar), so the user gets
the /r/<id> page with the timeline. Billing: 2 credits per second of SPEECH (silence is free).
Phones don't let apps hear calls, so this listens through a microphone.

MOCK_ALETHEIA set → a simulated stream (recorded spliced_en result), 0 credits.
"""
import asyncio
import json
import logging
import os
import time
import wave
from urllib.parse import urlencode

from app import config
from app.core import check as check_mod, normalize, store, verdict

log = logging.getLogger(__name__)

RATE = 16000
BYTES_PER_S = RATE * 2                 # 16-bit mono
MAX_FRAME = 64 * 1024                  # Aletheia's limit per binary frame
LIVE_MAX_SECONDS = int(os.getenv("LIVE_MAX_SECONDS", "300"))   # stop by itself: protects credits
LIVE_UPDATE_SECONDS = 5                # docs: 5-60, default 10. 10 felt sparse on stage (2 updates in 25 s);
                                       # billing is by speech seconds, not by update (phone test: 101 credits for 50 s)
# Live updates: "sure" = a fake verdict at this score or more. The page turns red only after two sure
# fake updates in a row (one alone: "possibly AI"); the final band uses verdict.decide_live().
LIVE_MIN_SCORE = verdict.LIVE_SURE
CLOSE_CODES = {4401: "auth", 4403: "auth", 4402: "out_of_credits", 4429: "busy", 1013: "busy"}


# --------------------------------------------------------------------------- the two streams

class AletheiaStream:
    """The real live stream. The API key goes in a header, never in the URL (the docs refuse that)."""

    def __init__(self, ws):
        self.ws, self.close_code = ws, None

    @classmethod
    async def open(cls, reference: str) -> "AletheiaStream":
        import websockets
        query = urlencode({"checks": "deepfake", "encoding": "pcm_s16le", "sample_rate": RATE,
                           "update_seconds": LIVE_UPDATE_SECONDS, "reference": reference})
        url = config.DETECTIF_BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/v1/stream?" + query
        ws = await websockets.connect(url, additional_headers={"Authorization": f"Bearer {config.DETECTIF_API_KEY}"},
                                      max_size=2 ** 22, open_timeout=15)
        return cls(ws)

    async def send_audio(self, frame: bytes) -> None:
        await self.ws.send(frame)

    async def send_stop(self) -> None:
        try:
            await self.ws.send(json.dumps({"type": "stop"}))
        except Exception:  # noqa: BLE001 — already closed
            pass

    async def recv(self) -> dict | None:
        import websockets
        try:
            return json.loads(await self.ws.recv())
        except websockets.ConnectionClosed as e:
            self.close_code = e.rcvd.code if e.rcvd else None
            return None

    async def close(self) -> None:
        await self.ws.close()


class MockStream:
    """Simulated stream for building and tests: every second counts as speech; the call's verdicts
    come from the recorded spliced_en result (fake part at 8-16 s), so the light goes red then green."""

    def __init__(self, reference: str):
        raw = json.loads((config.FIXTURES_DIR / "spliced_en.json").read_text(encoding="utf-8"))
        self.fakes = [(s["start"], s["end"]) for s in raw["result"]["segments"] if s.get("verdict") == "fake"]
        self.reference, self.received, self.sent_early, self.next_update = reference, 0, False, 10.0
        self.queue: asyncio.Queue = asyncio.Queue()
        self.queue.put_nowait({"type": "ready", "stream_id": "str_mock", "reference": reference, "checks": ["deepfake"]})
        self.close_code = None

    @classmethod
    async def open(cls, reference: str) -> "MockStream":
        return cls(reference)

    def _verdict(self, start: float, end: float) -> tuple[str, float]:
        fake = any(s < end and e > start for s, e in self.fakes)
        return ("fake", 0.97) if fake else ("real", 0.03)

    async def send_audio(self, frame: bytes) -> None:
        self.received += len(frame)
        t = self.received / BYTES_PER_S
        if not self.sent_early and t >= 6.0:
            self.sent_early = True
            v, sc = self._verdict(0, 6)
            await self.queue.put(self._update(True, t, 6.0, v, sc))
        if t >= self.next_update:
            v, sc = self._verdict(max(0.0, t - 20), t)
            await self.queue.put(self._update(False, t, min(t, 20.0), v, sc))
            self.next_update += LIVE_UPDATE_SECONDS

    def _update(self, early, t, window, v, score):
        return {"type": "deepfake", "early": early, "final": False, "seconds": round(t, 1), "speech_seconds": round(t, 1),
                "window_seconds": window, "verdict": v, "score": score, "reference": self.reference}

    async def send_stop(self) -> None:
        t = self.received / BYTES_PER_S
        if t < 2:
            res = {"object": "deepfake.detection", "final": True, "error": {"code": "insufficient_speech"}}
        else:
            segs, s = [], 0.0
            while s + 4 <= t + 1e-9 or not segs:
                v, sc = self._verdict(s, s + 4)
                segs.append({"start": s, "end": min(s + 4, round(t, 2)), "score": sc, "verdict": v})
                s += 2
            res = {"object": "deepfake.detection", "operation_id": None, "final": True,
                   "result": {"verdict": "real", "score": 0.25, "duration_seconds": round(t, 2),
                              "scored_seconds": round(t, 2), "segments": segs}}
        await self.queue.put({"type": "completed", "status": "completed", "seconds": round(t, 1),
                              "speech_seconds": round(t, 1), "ended_by": "client_stop", "results": {"deepfake": res},
                              "reference": self.reference})
        await self.queue.put(None)

    async def recv(self) -> dict | None:
        return await self.queue.get()

    async def close(self) -> None:
        pass


def open_stream(reference: str):
    return (MockStream if config.MOCK_ALETHEIA else AletheiaStream).open(reference)


# --------------------------------------------------------------------------- one session

async def run(browser, *, opener=None) -> None:
    """Serve one /ws/live connection (FastAPI WebSocket, already accepted) until the check is done."""
    sid = check_mod.new_id()
    wav_path = normalize.audio_dir() / f"live_{sid}.wav"

    async def tell(msg: dict) -> None:
        try:
            await browser.send_json(msg)
        except Exception:  # noqa: BLE001 — the page may be gone; the check still finishes
            pass

    try:
        up = await (opener or open_stream)(sid)
    except Exception as e:  # noqa: BLE001
        log.warning("live: could not open the stream: %s", e)
        await tell({"type": "error", "code": "unavailable"})
        return

    received, stopping = 0, False
    wav = wave.open(str(wav_path), "wb")
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(RATE)

    async def stop() -> None:
        nonlocal stopping
        if not stopping:
            stopping = True
            await up.send_stop()

    async def from_browser() -> None:
        nonlocal received
        while True:
            try:
                msg = await browser.receive()
            except Exception:  # noqa: BLE001
                break
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes") and not stopping:
                frame = msg["bytes"][:MAX_FRAME]
                frame = frame[:len(frame) - len(frame) % 2]
                wav.writeframes(frame)
                received += len(frame)
                await up.send_audio(frame)
                if received >= LIVE_MAX_SECONDS * BYTES_PER_S:
                    await tell({"type": "limit", "seconds": LIVE_MAX_SECONDS})
                    await stop()
            elif msg.get("text"):
                try:
                    kind = json.loads(msg["text"]).get("type")
                except ValueError:
                    kind = None
                if kind == "stop":
                    await stop()
        await stop()   # the page closed: still finish the check, so nothing is left half-open

    async def from_stream() -> dict | None:
        while (m := await up.recv()) is not None:
            kind = m.get("type")
            if kind == "ready":
                await tell({"type": "ready"})
            elif kind == "deepfake" and not m.get("final"):
                await tell({k: m.get(k) for k in ("early", "verdict", "score", "seconds", "speech_seconds",
                                                  "window_seconds")}
                           | {"type": "update", "sure": float(m.get("score") or 0) >= LIVE_MIN_SCORE})
            elif kind == "error":
                log.warning("live stream error: %s %s", m.get("code"), m.get("message"))
                await tell({"type": "error", "code": m.get("code") or "failed"})
            elif kind == "completed":
                return m
        return None

    t0 = time.perf_counter()
    reader = asyncio.create_task(from_browser())
    try:
        done = await from_stream()
    finally:
        reader.cancel()
        wav.close()
        try:
            await up.close()
        except Exception:  # noqa: BLE001
            pass

    res = ((done or {}).get("results") or {}).get("deepfake") or {}
    if not res.get("result"):
        code = (res.get("error") or {}).get("code") or CLOSE_CODES.get(getattr(up, "close_code", None), "failed")
        log.info("live %s: no result (%s), %.1f s of audio", sid, code, received / BYTES_PER_S)
        await tell({"type": "error", "code": code})
        wav_path.unlink(missing_ok=True)
        return

    result = save_result(sid, done, res, str(wav_path))
    log.info("live %s band=%s regions=%s speech=%s s %.0f s", result["id"], result["band"], result["core_regions"],
             done.get("speech_seconds"), time.perf_counter() - t0)
    await tell({"type": "result", "id": result["id"], "band": result["band"],
                "core_regions": result["core_regions"], "result_url": f"/r/{result['id']}"})


def save_result(sid: str, done: dict, res: dict, wav_path: str) -> dict:
    """The stream's final result → our verdict rules → stored like any check (channel "live")."""
    speech = float(done.get("speech_seconds") or res["result"].get("scored_seconds") or 0)
    raw = {"operation_id": res.get("operation_id"), "model": {"name": "aletheia", "version": "live stream"},
           "result": res["result"],
           "credits": {"charged": 0 if config.MOCK_ALETHEIA else max(store.MIN_CREDITS, round(speech * store.CREDITS_PER_SECOND))}}
    result = check_mod.build_result(raw, verdict.decide_live(res["result"]))
    result["id"] = sid
    result["result_url"] = check_mod.result_url(sid)
    # Aletheia's duration_seconds is the SPEECH length, but segment times are stream time (the WAV we
    # kept includes the silences): the timeline must span the whole stream, or late segments vanish
    stream_s = float(done.get("seconds") or 0)
    last_seg = max((float(s.get("end", 0)) for s in res["result"].get("segments") or []), default=0.0)
    result["duration"] = round(max(stream_s, last_seg, float(result.get("duration") or 0)), 2)
    result["live"] = {"seconds": done.get("seconds"), "speech_seconds": done.get("speech_seconds"),
                      "updates": res.get("updates"), "ended_by": done.get("ended_by")}
    store.save(result, source={"channel": "live"}, sha256=None, fp=None, duration=result["duration"],
               audio_path=wav_path)
    return result
