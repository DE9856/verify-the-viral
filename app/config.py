"""Settings from .env. Shared file: change only together."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DETECTIF_API_KEY = os.getenv("DETECTIF_API_KEY", "")
DETECTIF_BASE_URL = os.getenv("DETECTIF_BASE_URL", "https://platform.detectif.ai").rstrip("/")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
MOCK_ALETHEIA = os.getenv("MOCK_ALETHEIA", "").strip()
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
DB_PATH = ROOT / os.getenv("DB_PATH", "data/app.db")
FPCALC_PATH = os.getenv("FPCALC_PATH", "fpcalc")

FIXTURES_DIR = ROOT / "app" / "fixtures"
I18N_PATH = ROOT / "app" / "i18n.json"
WEB_DIR = ROOT / "app" / "web"

# Limits from the DetectifAI docs and the Telegram Bot API (see PLAN.md §1b)
MAX_SECONDS = 300            # Aletheia checks at most 5 minutes
TELEGRAM_MAX_BYTES = 20 * 1024 * 1024
RELIABLE_SPEECH_SECONDS = 10  # below this, results are much less reliable
