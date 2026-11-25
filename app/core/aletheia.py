"""Lane A · steps A1 (detect) and A3 (feedback) — REST client for DetectifAI Aletheia.

Docs: https://platform.detectif.ai/docs/deepfake-detection.md
- POST {DETECTIF_BASE_URL}/v1/deepfake/detect, multipart field "file",
  headers Authorization: Bearer <key>, Idempotency-Key: <sha256 of normalised audio>
- POST /v1/operations/{operation_id}/feedback  JSON {"correct": bool, "label": "real"|"fake"|null}
- Errors → AletheiaError(code=error.code): 402 insufficient_credits, 422 insufficient_speech /
  audio_too_long, 429/503 → wait Retry-After and retry with the SAME Idempotency-Key.
Use httpx.AsyncClient with timeout ≈ 120 s.
"""


class AletheiaError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: float | None = None):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message, self.retry_after = status, code, message, retry_after


async def detect(path: str, *, idempotency_key: str) -> dict:
    """Return the full JSON response (has "result", "operation_id", "model", "credits")."""
    raise NotImplementedError("Lane A · A1: aletheia.detect()")


async def feedback(operation_id: str, correct: bool, label: str | None = None) -> None:
    raise NotImplementedError("Lane A · A3: aletheia.feedback()")
