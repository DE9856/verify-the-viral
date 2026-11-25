"""Lane B · Telegram group guardian. Run: python -m app.bot

B1: voice / audio / video / video_note / audio-or-video document, in groups and DMs →
download (refuse > 20 MB before downloading) → check() → reply with the band text.
B2: per-chat language (default config.DEFAULT_LANG), /lang en|hi|kn (admins only in groups),
saved to data/chat_langs.json so it survives restarts.
Later: the card (B3), cache wording + 👍/👎 feedback (B4).
Gotcha: the bot only sees group media if privacy mode is disabled in @BotFather AND it was re-added.
"""
import json
import logging
import tempfile
from pathlib import Path

from telegram import BotCommand, Message, Update
from telegram.constants import ChatAction, ChatMemberStatus, ChatType
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import config
from app.core.check import check

log = logging.getLogger("bot")

I18N = json.loads(config.I18N_PATH.read_text(encoding="utf-8"))

MEDIA = (filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE
         | filters.Document.AUDIO | filters.Document.VIDEO)

LANGS = ("en", "hi", "kn")
LANG_FILE = config.ROOT / "data" / "chat_langs.json"

# default file endings when Telegram gives no file name
EXT = {"voice": ".ogg", "audio": ".mp3", "video": ".mp4", "video_note": ".mp4", "document": ""}


def t(key: str, lang: str, **kw) -> str:
    """Wording from app/i18n.json, falling back to English."""
    entry = I18N.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kw) if kw else text


# ---- per-chat language (B2) ----

def _load_langs() -> dict:
    try:
        return json.loads(LANG_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_chat_langs: dict = _load_langs()


def chat_lang(chat_id: int) -> str:
    lang = _chat_langs.get(str(chat_id), config.DEFAULT_LANG)
    return lang if lang in LANGS else "en"


def set_chat_lang(chat_id: int, lang: str) -> None:
    _chat_langs[str(chat_id)] = lang
    LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LANG_FILE.write_text(json.dumps(_chat_langs, indent=1), encoding="utf-8")


# ---- reply wording ----

def format_regions(regions: list, lang: str = "en") -> str:
    unit = t("seconds", lang)
    return ", ".join(f"{a:g}–{b:g} {unit}" for a, b in regions)


def format_reply(result: dict, lang: str) -> str:
    """The chat reply for one check() result (also the card caption later)."""
    if result["band"] == "error":
        code = (result.get("error") or {}).get("code", "failed")
        return t(f"error_{code}" if f"error_{code}" in I18N else "error_failed", lang)
    lines = [t(result["band"], lang, regions=format_regions(result.get("core_regions", []), lang))]
    if result.get("trimmed"):
        lines.append(t("trimmed", lang))
    if config.MOCK_ALETHEIA:
        # mock mode replays recorded results, unrelated to the clip sent: say so
        lines.append(t("mock_note", lang))
    return "\n".join(lines)


def pick_media(msg: Message):
    """Return (kind, telegram media object) for the first supported attachment, or (None, None)."""
    for kind in ("voice", "audio", "video", "video_note", "document"):
        media = getattr(msg, kind, None)
        if media is not None:
            return kind, media
    return None, None


# ---- handlers ----

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

    log.info("chat %s %s -> %s (%s)", msg.chat_id, kind, result["band"], lang)
    await msg.reply_text(format_reply(result, lang), do_quote=True)


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    await msg.reply_text(t("start", chat_lang(msg.chat_id)))


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat, user = update.effective_chat, update.effective_user
    if chat.type == ChatType.PRIVATE:
        return True
    if update.effective_message.sender_chat is not None:  # anonymous admin posting as the group
        return update.effective_message.sender_chat.id == chat.id
    if user is None:
        return False
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def on_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    current = chat_lang(msg.chat_id)
    choice = context.args[0].lower() if context.args else ""
    if choice not in LANGS:
        await msg.reply_text(t("lang_usage", current))
        return
    if not await is_admin(update, context):
        await msg.reply_text(t("lang_admins_only", current))
        return
    set_chat_lang(msg.chat_id, choice)
    log.info("chat %s language -> %s", msg.chat_id, choice)
    await msg.reply_text(t("lang_set", choice))


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([BotCommand("lang", "Language: en | hi | kn"),
                                   BotCommand("help", "How to use this bot")])


def build_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "help"], on_start))
    app.add_handler(CommandHandler("lang", on_lang))
    app.add_handler(MessageHandler(MEDIA, on_media))
    return app


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (see env.example)")
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    # httpx logs every request URL at INFO, and Telegram URLs contain the bot token: keep it quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    log.info("mock mode: %s · default language: %s", config.MOCK_ALETHEIA or "off (real API)",
             config.DEFAULT_LANG)
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
