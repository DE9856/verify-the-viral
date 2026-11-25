"""Day 0 · D1 "done when": your API key works. Prints your DetectifAI credit balance.
Run: python -m scripts.credits"""
import httpx

from app import config

if not config.DETECTIF_API_KEY:
    raise SystemExit("Set DETECTIF_API_KEY in .env first (copy env.example to .env)")

r = httpx.get(f"{config.DETECTIF_BASE_URL}/v1/credits",
              headers={"Authorization": f"Bearer {config.DETECTIF_API_KEY}"}, timeout=30)
if r.status_code != 200:
    raise SystemExit(f"{r.status_code}: {r.text[:300]}")
d = r.json()
print(f"plan={d.get('plan')}  available={d.get('available')}  reserved={d.get('reserved')}  "
      f"min per check={d.get('price_per_operation')}")
if d.get("available") is not None:
    print(f"≈ {d['available'] // 60} checks of a 30-second clip (2 credits per second)")
