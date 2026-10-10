"""Telegram webhook (Lambda Function URL). Joins with consent, status, stop, language, engineer and field-kit buttons.

Callback data (max 64 bytes): s:<v|e>:<key>:<y|n> consent · j:<village key> pick village ·
f:<short>:<action> fix · x:<case id> close attempt · k:<short>:<clean|contaminated> kit result ·
l:<hi|en>:<village key> read the village's alerts in another language · g:<hi|en>:<v|e>:<key> consent in another language.
"""

from __future__ import annotations

import base64
import hmac
import json
import logging
import os

from . import actions, case_steps, config, i18n, store, telegram, views, vision

log = logging.getLogger()
log.setLevel(logging.INFO)


def _ok(body: str = "ok"):
    return {"statusCode": 200, "body": body}


def _authorised(event) -> bool:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    supplied = headers.get("x-telegram-bot-api-secret-token", "")
    return hmac.compare_digest(supplied, config.secret(config.SSM_WEBHOOK_SECRET))


def _block_name(block_key: str, lang: str) -> str:
    cases = store.block_cases(block_key)
    name = cases[0].get("block") if cases else None
    return i18n.t("block_label", lang, name=name or block_key)


def _consent(chat_id: int, role: str, key: str, lang: str) -> None:
    if role == "v":
        v = store.get_village(key)
        label, who = (v or {}).get("name", key), i18n.t("who_village", lang)
    else:
        label, who = _block_name(key, lang), i18n.t("who_block", lang)
    rows = [[(i18n.t("yes", lang), f"s:{role}:{key}:y"), (i18n.t("no", lang), f"s:{role}:{key}:n")]]
    switch = f"g:{i18n.other(lang)}:{role}:{key}"
    if len(switch) <= 64:
        rows.append([(i18n.t("switch_to", lang), switch)])
    telegram.send_message(chat_id, i18n.t("consent", lang, label=label, who=who), rows)


def _village_picker(chat_id: int, lang: str) -> None:
    villages = sorted(store.list_villages(),
                      key=lambda v: (v.get("source") != "fixtures", v.get("district") or "", v.get("name") or ""))[:12]
    rows = [[(f"{v['name']} ({v.get('block') or v.get('district')})", f"j:{v['key']}")] for v in villages]
    telegram.send_message(chat_id, i18n.t("help", lang), rows or None)


def _status(chat_id: int, lang: str) -> None:
    subs = store.chat_subscriptions(chat_id)
    if not subs:
        telegram.send_message(chat_id, i18n.t("not_joined", lang))
        return
    lines = []
    for s in subs:
        kind, key = s["scope_pk"].split("#", 1)
        if kind == "VILLAGE" and (b := views.village_bundle(key)):
            lines.append(f"• <b>{b['village']['name']}</b>: {b['status_text'][lang]}")
        elif kind == "BLOCK":
            open_cases = [c for c in store.block_cases(key) if c.get("status") in store.OPEN_STATUSES]
            lines.append(i18n.t("status_block", lang, block=_block_name(key, lang), n=len(open_cases)))
    telegram.send_message(chat_id, "\n".join(lines))


def _command(u: dict) -> None:
    chat, cmd, arg = u["chat_id"], u["command"], u.get("arg", "")
    if cmd in ("/english", "/hindi", "/lang"):
        lang = {"/english": "en", "/hindi": "hi"}.get(cmd) or i18n.other(store.chat_lang(chat))
        store.set_chat_lang(chat, lang)
        telegram.send_message(chat, i18n.t("lang_set", lang))
        return
    lang = store.chat_lang(chat)
    if cmd == "/start" and arg[:2] in ("v_", "e_"):
        role, key = arg[0], arg[2:]
        if role == "v" and not store.get_village(key):
            telegram.send_message(chat, i18n.t("village_not_found", lang))
            return
        _consent(chat, role, key, lang)
    elif cmd in ("/start", "/help"):
        _village_picker(chat, lang)
    elif cmd == "/status":
        _status(chat, lang)
    elif cmd == "/stop":
        n = store.unsubscribe_all(chat)
        telegram.send_message(chat, i18n.t("stopped", lang, n=n))
    else:
        telegram.send_message(chat, i18n.t("help", lang))


def _village_of(chat_id: int) -> str | None:
    subs = [s for s in store.chat_subscriptions(chat_id) if s["scope_pk"].startswith("VILLAGE#")]
    return subs[0]["scope_pk"].split("#", 1)[1] if subs else None


def _ask(u: dict) -> None:
    """A question by voice or text: acknowledge now, answer from an async run of this function (Ask JalSaathi)."""
    from . import assistant

    chat, lang = u["chat_id"], store.chat_lang(u["chat_id"])
    key = _village_of(chat)
    if not key:
        telegram.send_message(chat, i18n.t("ask_join_first", lang))
        return
    if u["kind"] == "voice" and (u.get("duration") or 0) > assistant.MAX_VOICE_SECONDS:
        telegram.send_message(chat, i18n.t("ask_too_long", lang))
        return
    job = {"chat_id": chat, "village_key": key, "lang": lang}
    job.update(file_id=u["file_id"]) if u["kind"] == "voice" else job.update(text=u["text"][:500])
    telegram.send_message(chat, i18n.t("ask_wait", lang))
    config.client("lambda").invoke(FunctionName=os.environ.get("AWS_LAMBDA_FUNCTION_NAME", ""), InvocationType="Event",
                                   Payload=json.dumps({"assistant": job}).encode())


def _store_kit_photo(chat_id: int, case_id: str) -> tuple[str | None, dict | None]:
    pending = store.pop_pending_photo(chat_id)
    if not pending:
        return None, None
    file_id = pending["file_id"]
    key = f"private/kit/{case_id}/{file_id[-16:]}.jpg"
    config.client("s3").put_object(Bucket=config.bucket(), Key=key, Body=telegram.download_file(file_id), ContentType="image/jpeg")
    return key, pending.get("hint")


def _photo(u: dict) -> None:
    """A field-kit photo. Village relays get an AI suggestion of the vial colour; the person still chooses."""
    hint = None
    if any(s["scope_pk"].startswith("VILLAGE#") for s in store.chat_subscriptions(u["chat_id"])):
        hint = vision.kit_hint(telegram.download_file(u["file_id"]))
    store.put_pending_photo(u["chat_id"], u["file_id"], hint)
    telegram.send_message(u["chat_id"], vision.hint_message(hint, store.chat_lang(u["chat_id"])))


def _callback(u: dict) -> None:
    chat, data, cb = u["chat_id"], u["data"], u["callback_id"]
    actor = f"tg:{chat}"
    parts = data.split(":")
    lang = store.chat_lang(chat)
    try:
        if parts[0] == "l" and len(parts) == 3 and parts[1] in i18n.LANGS:
            store.set_chat_lang(chat, parts[1])
            telegram.answer_callback(cb, i18n.t("lang_set", parts[1]))
            case_steps.send_village_alerts(parts[2], chat, parts[1])
        elif parts[0] == "g" and len(parts) == 4 and parts[1] in i18n.LANGS:
            store.set_chat_lang(chat, parts[1])
            telegram.clear_buttons(chat, u["message_id"])
            telegram.answer_callback(cb)
            _consent(chat, parts[2], parts[3], parts[1])
        elif parts[0] == "j" and len(parts) == 2:
            telegram.answer_callback(cb)
            if store.get_village(parts[1]):
                _consent(chat, "v", parts[1], lang)
        elif parts[0] == "s" and len(parts) == 4:
            role, key, yes = parts[1], parts[2], parts[3] == "y"
            telegram.clear_buttons(chat, u["message_id"])
            if not yes:
                store.unsubscribe_all(chat)
                telegram.answer_callback(cb, i18n.t("declined", lang))
                return
            scope = f"VILLAGE#{key}" if role == "v" else f"BLOCK#{key}"
            store.subscribe(chat, "relay" if role == "v" else "engineer", scope, u.get("name"))
            telegram.answer_callback(cb, i18n.t("joined_toast", lang))
            if role == "v":
                bundle = views.village_bundle(key)
                telegram.send_message(chat, i18n.t("joined_village", lang, name=bundle["village"]["name"],
                                                   status=bundle["status_text"][lang]))
                case_steps.send_village_alerts(key, chat)
            else:
                telegram.send_message(chat, i18n.t("joined_engineer", lang, block=_block_name(key, lang)))
                if not case_steps.catch_up_engineer(chat, key):
                    telegram.send_message(chat, i18n.t("no_open_cases", lang))
        elif parts[0] == "f" and len(parts) == 3:
            case_id = actions.case_for_short(parts[1], "fix")
            actions.log_fix(case_id, parts[2], actor)
            telegram.clear_buttons(chat, u["message_id"])
            telegram.answer_callback(cb, i18n.t("logged_toast", lang))
            telegram.send_message(chat, i18n.t("fix_logged", lang, action=i18n.t(f"fix_{parts[2]}", lang)))
        elif parts[0] == "x" and len(parts) == 2:
            d = actions.try_close(parts[1], actor)
            telegram.answer_callback(cb, i18n.t("close_allowed" if d["allowed"] else "close_denied", lang), alert=True)
        elif parts[0] == "k" and len(parts) == 3:
            case_id = actions.case_for_short(parts[1], "kit")
            if config.kit_photo_required() and not store.has_pending_photo(chat):
                telegram.answer_callback(cb, i18n.t("photo_first", lang), alert=True)
                return
            actions.require_waiting(case_id, "kit")  # fail before the photo is consumed
            photo, hint = _store_kit_photo(chat, case_id)
            actions.kit_result(case_id, parts[2], actor, photo, hint)
            telegram.clear_buttons(chat, u["message_id"])
            telegram.answer_callback(cb, i18n.t("result_logged", lang))
        else:
            telegram.answer_callback(cb)
    except actions.ActionError as exc:
        telegram.answer_callback(cb, str(exc), alert=True)


def handler(event, context=None):
    if "assistant" in event:  # our own async invoke (never reachable through the function URL)
        from . import assistant

        return assistant.handle_telegram(event["assistant"])
    if not _authorised(event):
        return {"statusCode": 401, "body": "unauthorised"}
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    u = telegram.parse_update(json.loads(body))
    if u.get("update_id") is not None and store.seen_update(u["update_id"]):
        return _ok("duplicate")
    try:
        if u["kind"] == "command":
            _command(u)
        elif u["kind"] == "callback":
            _callback(u)
        elif u["kind"] == "photo":
            _photo(u)
        elif u["kind"] == "voice":
            _ask(u)
        elif u["kind"] == "text":
            if _village_of(u["chat_id"]):
                _ask(u)
            else:
                telegram.send_message(u["chat_id"], i18n.t("help", store.chat_lang(u["chat_id"])))
    except Exception:  # noqa: BLE001 - always 200 so Telegram doesn't retry forever
        log.exception("webhook handling failed")
    return _ok()
