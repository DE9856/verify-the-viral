"""Lane B · Telegram group guardian. Run: python -m app.bot

B1: voice / audio / video / video_note / audio-or-video document, in groups and DMs →
download (refuse > 20 MB before downloading) → check() → reply with the band text.
Later: per-group language (B2), the card (B3), cache wording + 👍/👎 feedback (B4).
Gotcha: the bot only sees group media if privacy mode is disabled in @BotFather AND it was re-added.
"""
import json
import logging
import tempfile
from pathlib import Path

from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import config
from app.core.check import check

log = logging.getLogger("bot")

I18N = json.loads(config.I18N_PATH.read_text(encoding="utf-8"))

MEDIA = (filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE
         | filters.Document.AUDIO | filters.Document.VIDEO)

# Mock mode replays recorded results, so the reply has nothing to do with the clip sent: say so.
MOCK_NOTE = "🧪 Test mode: this is a recorded sample result, not a check of your clip."

# default file endings when Telegram gives no file name
EXT = {"voice": ".ogg", "audio": ".mp3", "video": ".mp4", "video_note": ".mp4", "document": ""}


def t(key: str, lang: str, **kw) -> str:
    """Wording from app/i18n.json, falling back to English."""
    entry = I18N.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kw) if kw else text


def chat_lang(chat_id: int) -> str:
    return config.DEFAULT_LANG  # B2: per-group /lang en|hi|kn


def format_regions(regions: list) -> str:
    return ", ".join(f"{a:g}–{b:g} s" for a, b in regions)


def format_reply(result: dict, lang: str) -> str:
    """The chat reply for one check() result (also the card caption later)."""
    if result["band"] == "error":
        code = (result.get("error") or {}).get("code", "failed")
        return t(f"error_{code}" if f"error_{code}" in I18N else "error_failed", lang)
    lines = [t(result["band"], lang, regions=format_regions(result.get("core_regions", [])))]
    if result.get("trimmed"):
        lines.append(t("trimmed", lang))
    if config.MOCK_ALETHEIA:
        lines.append(MOCK_NOTE)
    return "\n".join(lines)


def pick_media(msg: Message):
    """Return (kind, telegram media object) for the first supported attachment, or (None, None)."""
    for kind in ("voice", "audio", "video", "video_note", "document"):
        media = getattr(msg, kind, None)
        if media is not None:
            return kind, media
    return None, None


async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    kind, media = pick_media(msg)
    if media is None:
        return
    lang = chat_lang(msg.chat_id)
    if (media.file_size or 0) > config.TELEGRAM_MAX_BYTES:
        await msg.reply_text(t("error_too_large", lang), do_quote=True)
        return

    await context.bot.send_chat_action(msg.chat_id, ChatAction.TYPING)
    filename = getattr(media, "file_name", None) or f"{kind}{EXT[kind]}"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / Path(filename).name
            tg_file = await media.get_file()
            await tg_file.download_to_drive(path)
            result = await check(str(path), source={"channel": "telegram",
                                                    "tg_file_unique_id": media.file_unique_id,
                                                    "filename": filename})
    except Exception:
        log.exception("check failed for %s in chat %s", kind, msg.chat_id)
        await msg.reply_text(t("error_failed", lang), do_quote=True)
        return

    log.info("chat %s %s -> %s", msg.chat_id, kind, result["band"])
    await msg.reply_text(format_reply(result, lang), do_quote=True)


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Send or forward a voice note, audio or video and I'll check whether the voice is AI-generated.\n"
        "In a group, just add me: I check every voice note and video.")


def build_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], on_start))
    app.add_handler(MessageHandler(MEDIA, on_media))
    return app


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (see env.example)")
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    # httpx logs every request URL at INFO, and Telegram URLs contain the bot token: keep it quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    log.info("mock mode: %s", config.MOCK_ALETHEIA or "off (real API)")
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
