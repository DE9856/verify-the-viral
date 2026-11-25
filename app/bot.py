"""Lane B · step B1 — Telegram group guardian. Run: python -m app.bot

To build (PLAN.md §5.4):
- python-telegram-bot 22.x, long polling (Application.builder().token(...).build().run_polling()).
- Handlers for voice, audio, video, video_note and document (audio/video MIME) in groups and DMs.
- Refuse files over config.TELEGRAM_MAX_BYTES (20 MB) politely, before downloading.
- Download to a temp file → await check(path, source={"channel": "telegram",
  "tg_file_unique_id": <file.file_unique_id>, "filename": ...}) → reply in the group's language
  with text from app/i18n.json (B2), later the card (B3) and 👍/👎 feedback buttons (B4).
- The bot only sees group voice notes if privacy mode is disabled in @BotFather AND it was re-added.
"""
from app import config


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (see env.example)")
    raise NotImplementedError("Lane B · B1: build the bot")


if __name__ == "__main__":
    main()
