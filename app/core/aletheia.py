"""Lane A · steps A1 (detect) and A3 (feedback) — REST client for DetectifAI Aletheia.

Docs: https://platform.detectif.ai/docs/deepfake-detection.md and /docs/#errors
- One shared httpx.AsyncClient; at most ALETHEIA_CONCURRENCY uploads at once (default 2), so the
  bot and a burst of group forwards don't trip 429 concurrency_limited.
- Retries reuse the SAME Idempotency-Key, so a retry is never charged twice:
  429 / 503 / 409 operation_in_progress → wait Retry-After (capped); 500 / 502 / 504 / network → backoff.
- Other 4xx → AletheiaError with the stable error.code (insufficient_speech, insufficient_credits, …).
"""
import asyncio
import logging
import mimetypes
import os
from pathlib import Path

import httpx

from app import config

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
MAX_WAIT = 8.0
RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504}
CONCURRENCY = int(os.getenv("ALETHEIA_CONCURRENCY", "2"))
_client: httpx.AsyncClient | None = None
_sem: asyncio.Semaphore | None = None
_loop: asyncio.AbstractEventLoop | None = None        # client + semaphore belong to one event loop
_transport: httpx.AsyncBaseTransport | None = None   # tests inject httpx.MockTransport here


class AletheiaError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: float | None = None):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message, self.retry_after = status, code, message, retry_after


def use_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """For tests: route all calls through a fake transport."""
    global _client, _transport
    _transport, _client = transport, None


def _bind_loop() -> None:
    global _client, _sem, _loop
    loop = asyncio.get_running_loop()
    if _client is None or _loop is not loop:
        _loop = loop
        _client = httpx.AsyncClient(base_url=config.DETECTIF_BASE_URL, transport=_transport,
                                    timeout=httpx.Timeout(150.0, connect=10.0))
        _sem = asyncio.Semaphore(CONCURRENCY)


def _get_client() -> httpx.AsyncClient:
    _bind_loop()
    return _client


def _auth() -> dict:
    if not config.DETECTIF_API_KEY:
        raise AletheiaError(401, "missing_api_key", "DETECTIF_API_KEY is not set in .env")
    return {"Authorization": f"Bearer {config.DETECTIF_API_KEY}"}


def _error_from(resp: httpx.Response) -> AletheiaError:
    try:
        err = resp.json().get("error", {})
    except ValueError:
        err = {}
    ra = resp.headers.get("retry-after")
    return AletheiaError(resp.status_code, err.get("code", f"http_{resp.status_code}"),
                         err.get("message", resp.text[:200]), float(ra) if ra and ra.replace(".", "").isdigit() else None)


async def _request(method: str, url: str, *, retry_key: str | None = None, **kw) -> httpx.Response:
    last: AletheiaError | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = await _get_client().request(method, url, **kw)
        except httpx.TransportError as e:            # network blip, timeout
            last = AletheiaError(0, "network_error", str(e) or type(e).__name__)
        else:
            if resp.status_code < 400:
                return resp
            last = _error_from(resp)
            if resp.status_code not in RETRY_STATUSES or (resp.status_code == 409 and last.code != "operation_in_progress"):
                raise last
        if attempt + 1 < MAX_ATTEMPTS:
            wait = min(last.retry_after or (0.5 * 2 ** attempt), MAX_WAIT)
            log.warning("aletheia %s %s → %s; retry %d in %.1fs (key %s)", method, url, last.code,
                        attempt + 1, wait, (retry_key or "")[:12])
            await asyncio.sleep(wait)
    raise last


async def detect(path: str, *, idempotency_key: str) -> dict:
    """Return the full JSON response (has "result", "operation_id", "model", "credits")."""
    data = Path(path).read_bytes()
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    headers = {**_auth(), "Idempotency-Key": idempotency_key[:128]}
    _bind_loop()
    async with _sem:
        resp = await _request("POST", "/v1/deepfake/detect", retry_key=idempotency_key, headers=headers,
                              files={"file": (Path(path).name, data, mime)})
    return resp.json()


async def feedback(operation_id: str, correct: bool, label: str | None = None) -> None:
    body = {"correct": correct, **({"label": label} if label in ("real", "fake") else {})}
    await _request("POST", f"/v1/operations/{operation_id}/feedback", headers=_auth(), json=body)


async def credits() -> dict:
    return (await _request("GET", "/v1/credits", headers=_auth())).json()


async def health(timeout: float = 3.0) -> dict:
    """Upstream status; needs no key. Never raises."""
    try:
        resp = await _get_client().get("/v1/health", timeout=timeout)
        return resp.json() if resp.status_code == 200 else {"status": f"http_{resp.status_code}"}
    except Exception as e:  # noqa: BLE001 — health must not fail the caller
        return {"status": "unreachable", "detail": type(e).__name__}
