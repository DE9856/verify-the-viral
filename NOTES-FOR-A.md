# Notes for Lane A (from Lane B)

## 2026-11-25 — segment verdicts use their own threshold (affects A2 `verdict.py`)
In our real-voice test (`research/real-world.md`) a Hindi segment scored **0.883** and still came
back `"verdict": "real"`, while the overall threshold in the response is 0.62. So in `verdict.py`
decide "fake window" by each segment's `verdict` field, not by `score > threshold`.
Also: 0 false alarms on 12 real clips (en/hi/kn, clean + WhatsApp-quality); Hindi runs hottest.
