"""Telegram Bot API client and update parsing. The channel adapter (send_*) is what WhatsApp would replace later."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from . import config

log = logging.getLogger(__name__)


class TelegramError(RuntimeError):
    pass


def _call(method: str, **params):
    url = f"https://api.telegram.org/bot{config.secret(config.SSM_BOT_TOKEN)}/{method}"
    data = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as exc:  # keep Telegram's description, never the URL (it holds the token)
        body = json.loads(exc.read() or b"{}")
    if not body.get("ok"):
        raise TelegramError(f"{method}: {body.get('description', 'unknown error')}")
    return body["result"]


def keyboard(rows: list[list[tuple[str, str]]] | None) -> dict | None:
    """rows of (label, callback_data or https URL)."""
    if not rows:
        return None
    return {"inline_keyboard": [[{"text": label, **({"url": data} if data.startswith("https://") else {"callback_data": data})}
                                 for label, data in row] for row in rows]}


def send_message(chat_id: int, text: str, buttons=None) -> dict:
    return _call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True,
                 reply_markup=keyboard(buttons))


def send_audio(chat_id: int, audio_url: str, caption: str | None = None, title: str | None = None) -> dict:
    return _call("sendAudio", chat_id=chat_id, audio=audio_url, caption=caption, title=title, performer="JalSaathi")


def answer_callback(callback_id: str, text: str | None = None, alert: bool = False) -> None:
    try:
        _call("answerCallbackQuery", callback_query_id=callback_id, text=text, show_alert=alert)
    except TelegramError as exc:
        log.warning("answerCallbackQuery failed: %s", exc)


def clear_buttons(chat_id: int, message_id: int) -> None:
    try:
        _call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup={"inline_keyboard": []})
    except TelegramError as exc:
        log.info("clear buttons: %s", exc)


def download_file(file_id: str) -> bytes:
    info = _call("getFile", file_id=file_id)
    url = f"https://api.telegram.org/file/bot{config.secret(config.SSM_BOT_TOKEN)}/{info['file_path']}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def parse_update(update: dict) -> dict:
    """Normalise a Telegram update into {kind, update_id, chat_id, ...}."""
    out = {"update_id": update.get("update_id"), "kind": "other"}
    if cb := update.get("callback_query"):
        msg = cb.get("message") or {}
        out.update(kind="callback", callback_id=cb.get("id"), data=cb.get("data") or "",
                   chat_id=(msg.get("chat") or {}).get("id"), message_id=msg.get("message_id"),
                   name=(cb.get("from") or {}).get("first_name"))
        return out
    msg = update.get("message") or {}
    if not msg:
        return out
    out.update(chat_id=(msg.get("chat") or {}).get("id"), name=(msg.get("from") or {}).get("first_name"),
               message_id=msg.get("message_id"))
    if photos := msg.get("photo"):
        out.update(kind="photo", file_id=photos[-1]["file_id"])  # largest size is last
    elif (text := (msg.get("text") or "").strip()).startswith("/"):
        command, _, arg = text.partition(" ")
        out.update(kind="command", command=command.split("@")[0].lower(), arg=arg.strip())
    elif text:
        out.update(kind="text", text=text)
    return out
