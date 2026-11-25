"""Lane B · Telegram group guardian. Run: python -m app.bot

B1: voice / audio / video / video_note / audio-or-video document, in groups and DMs →
download (refuse > 20 MB before downloading) → check() → reply with the band text.
B2: per-chat language (default config.DEFAULT_LANG), /lang en|hi|kn (admins only in groups),
saved to data/chat_langs.json so it survives restarts.
B3: the verdict card (app/core/card.py) as a photo with the reply text as caption;
falls back to text if the card can't be drawn. Chromium is warmed up at startup.
B4: "Already checked N times" on cache hits; a button to the timeline page (only when
PUBLIC_BASE_URL is a public https address: Telegram rejects localhost links); in groups a
one-line ✅ for 🟢 instead of the full card; "Was this right? 👍 / 👎" → send_feedback().
Sync 1: a "⏳ Checking…" message if check() takes over 1.5 s (deleted when the answer arrives).
"Hear the fake part": for 🟠 partly fake, the flagged seconds follow the card as a voice note
(app/core/excerpt.py), so people hear what was edited in without opening a link.
Gotcha: the bot only sees group media if privacy mode is disabled in @BotFather AND it was re-added.
"""
import asyncio
import json
import logging
import tempfile
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ChatMemberStatus, ChatType
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from app import config
from app.core import card, excerpt
from app.core.check import check, send_feedback

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


def variant_note(cache: dict, lang: str) -> str | None:
    """'This is a 1.5× speed copy…' when the cache matched a sped-up / slowed / pitch-shifted copy."""
    v = cache.get("variant") or {}
    if v.get("kind") in ("speed", "tape") and v.get("speed"):
        return t("cache_variant_speed", lang, speed=f"{v['speed']:g}")
    if v.get("kind") == "pitch":
        return t("cache_variant_pitch", lang)
    return None


def format_reply(result: dict, lang: str) -> str:
    """The chat reply for one check() result (also the card caption later)."""
    if result["band"] == "error":
        code = (result.get("error") or {}).get("code", "failed")
        return t(f"error_{code}" if f"error_{code}" in I18N else "error_failed", lang)
    lines = [t(result["band"], lang, regions=format_regions(result.get("core_regions", []), lang))]
    if result.get("trimmed"):
        lines.append(t("trimmed", lang))
    cache = result.get("cache") or {}
    if cache.get("hit"):
        lines.append(t("cache_hit", lang, n=cache.get("times_checked", 2)))
        if note := variant_note(cache, lang):
            lines.append(note)
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


# ---- B4: group etiquette, timeline button, feedback buttons ----

# one letter per band keeps callback_data under Telegram's 64-byte limit
BAND_CODE = {"likely_fake": "l", "partly_fake": "p", "unclear": "u", "no_signs": "n"}
CODE_BAND = {v: k for k, v in BAND_CODE.items()}


def is_group(msg: Message) -> bool:
    return msg.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


def short_reply(result: dict, msg: Message) -> bool:
    """In groups, a clean result gets one quiet line instead of the full card."""
    return result["band"] == "no_signs" and is_group(msg)


def public_link(url: str) -> bool:
    return url.startswith("https://") and "localhost" not in url and "127.0.0.1" not in url


def feedback_label(band: str, correct: bool) -> str | None:
    """What the clip really is, from the user's 👍/👎 on our verdict (None if we can't tell)."""
    said = {"likely_fake": "fake", "partly_fake": "fake", "no_signs": "real"}.get(band)
    if said is None:
        return None
    return said if correct else ("real" if said == "fake" else "fake")


def keyboard(result: dict, lang: str, with_feedback: bool = True) -> InlineKeyboardMarkup | None:
    rows = []
    if with_feedback:
        op = result.get("operation_id") or result["id"]
        code = BAND_CODE[result["band"]]
        rows.append([InlineKeyboardButton("👍", callback_data=f"fb:1:{code}:{op}"),
                     InlineKeyboardButton("👎", callback_data=f"fb:0:{code}:{op}")])
    if public_link(result.get("result_url", "")):
        rows.append([InlineKeyboardButton(t("view_timeline", lang), url=f"{result['result_url']}?lang={lang}")])
    return InlineKeyboardMarkup(rows) if rows else None


def parse_feedback(data: str):
    """'fb:1:p:op_123' → (True, 'partly_fake', 'op_123'), or None if it isn't ours."""
    parts = data.split(":", 3)
    if len(parts) != 4 or parts[0] != "fb" or parts[1] not in ("0", "1") or parts[2] not in CODE_BAND:
        return None
    return parts[1] == "1", CODE_BAND[parts[2]], parts[3]


async def send_fake_part(reply_to: Message, result: dict, lang: str) -> None:
    """🟠 partly fake: reply with the flagged seconds as a voice note. Never breaks the reply."""
    try:
        part = await excerpt.fake_part(result)
        if not part:
            return
        path, region = part
        caption = t("fake_part_caption", lang, regions=format_regions([region], lang))
        with open(path, "rb") as f:
            await reply_to.reply_voice(f, caption=caption, do_quote=True)
    except Exception:
        log.exception("could not send the fake part for %s", result.get("id"))


CHECKING_AFTER_S = 1.5


async def _delete(message) -> None:
    if message is not None:
        try:
            await message.delete()
        except Exception:
            log.debug("could not delete checking message", exc_info=True)


# ---- handlers ----

async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    kind, media = pick_media(msg)
    if media is None:
        return
    lang = chat_lang(msg.chat_id)
    checking = None
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
            task = asyncio.create_task(check(str(path), source={
                "channel": "telegram", "tg_file_unique_id": media.file_unique_id, "filename": filename,
                # only a salted hash is stored, to count chats on the AI-clip radar (store.place_of)
                "chat_id": msg.chat_id}))
            # a cache hit answers at once; a real API call can take seconds → say we're on it
            done, _ = await asyncio.wait({task}, timeout=CHECKING_AFTER_S)
            if not done:
                checking = await msg.reply_text(t("checking", lang), do_quote=True)
            result = await task
    except Exception:
        log.exception("check failed for %s in chat %s", kind, msg.chat_id)
        await _delete(checking)
        await msg.reply_text(t("error_failed", lang), do_quote=True)
        return
    await _delete(checking)

    log.info("chat %s %s -> %s (%s)%s", msg.chat_id, kind, result["band"], lang,
             " cache hit" if (result.get("cache") or {}).get("hit") else "")
    if result["band"] == "error":
        await msg.reply_text(format_reply(result, lang), do_quote=True)
        return
    if short_reply(result, msg):
        cache = result.get("cache") or {}
        line = t("short_no_signs", lang)
        if cache.get("hit"):
            line += " " + t("cache_hit", lang, n=cache.get("times_checked", 2))
            if note := variant_note(cache, lang):
                line += " " + note
        await msg.reply_text(line, do_quote=True,
                             reply_markup=keyboard(result, lang, with_feedback=False))
        return

    text = format_reply(result, lang) + "\n\n" + t("feedback_question", lang)
    markup = keyboard(result, lang)
    try:
        png = await card.render_card(result, lang)
        sent = await msg.reply_photo(png, caption=text, do_quote=True, reply_markup=markup)
    except Exception:
        log.exception("card failed, sending text only")
        sent = await msg.reply_text(text, do_quote=True, reply_markup=markup)
    if result["band"] == "partly_fake":
        await send_fake_part(sent, result, lang)


async def on_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parsed = parse_feedback(query.data or "")
    lang = chat_lang(query.message.chat_id) if query.message else config.DEFAULT_LANG
    if parsed is None:
        await query.answer()
        return
    correct, band, op = parsed
    done = context.bot_data.setdefault("feedback_done", set())
    if op in done:  # one answer per check, even if two people tap at once
        await query.answer(t("feedback_already", lang))
        return
    done.add(op)
    try:
        await send_feedback(op if op.startswith("op_") else "", correct, feedback_label(band, correct))
    except Exception:
        log.exception("send_feedback failed for %s", op)
    log.info("feedback %s correct=%s band=%s", op, correct, band)
    await query.answer(t("feedback_thanks", lang))
    # drop the 👍/👎 row, keep the timeline link
    rows = [r for r in (query.message.reply_markup.inline_keyboard if query.message and query.message.reply_markup else [])
            if not any((b.callback_data or "").startswith("fb:") for b in r)]
    try:
        await query.edit_message_reply_markup(InlineKeyboardMarkup(rows) if rows else None)
    except Exception:
        log.debug("could not edit buttons", exc_info=True)


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
    try:
        await card.start()  # warm Chromium now so the first card isn't slow
    except Exception:
        log.exception("card renderer failed to start; replies will be text only")


async def post_shutdown(app: Application) -> None:
    await card.close()


def build_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    app.add_handler(CommandHandler(["start", "help"], on_start))
    app.add_handler(CommandHandler("lang", on_lang))
    app.add_handler(CallbackQueryHandler(on_feedback, pattern=r"^fb:"))
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
    from app.core import fingerprint
    if fp := fingerprint.fpcalc_path():
        log.info("fpcalc: %s (re-encoded forwards hit the cache)", fp)
    else:
        log.warning("!!! fpcalc NOT FOUND: a re-encoded forward (WhatsApp, MP3) will be checked again "
                    "and cost credits. Windows: put fpcalc.exe in bin/. Fedora: sudo dnf install chromaprint-tools")
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
