# Deploy / run (updated 2026-11-26)
- Server = Fedora laptop (bot + API + ngrok). Start from the repo root: `ngrok http --url=spirits-bauble-astronomy.ngrok-free.dev 8000`, `uvicorn app.api:app --host 127.0.0.1 --port 8000`, `python -m app.bot`. PUBLIC_BASE_URL needs `https://`. Only one bot process per token.
- Clean tests: `DB_PATH=data/<name>.db` in the shell overrides `.env` (load_dotenv doesn't override).
- PWA share target: Android Chrome, installed, HTTPS on a STABLE origin. ngrok free serves a "Visit Site" page to cookie-less fetches: manifest links need `crossorigin="use-credentials"`. Fallback: Tailscale Funnel.
- Env template is `env.example` (no dot): a permission rule blocks Claude from `.env*` files.
- Bot @verifytheviralbot: privacy mode off + re-add to groups; httpx logger stays at WARNING (URLs carry the token).
- Windows Bash commits: `git commit -F file` (PowerShell 5.1 splits here-strings).
