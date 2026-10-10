"""Telegram webhook (Lambda Function URL). Joins with consent, status, stop, engineer and field-kit buttons.

Callback data (max 64 bytes): s:<v|e>:<key>:<y|n> consent · j:<village key> pick village ·
f:<short>:<action> fix · x:<case id> close attempt · k:<short>:<clean|contaminated> kit result.
"""

from __future__ import annotations

import base64
import hmac
import json
import logging

from . import actions, case_steps, config, store, telegram, views, vision

log = logging.getLogger()
log.setLevel(logging.INFO)

HELP = ("💧 <b>JalSaathi</b>\nसरकारी लैब जांच में गाँव का पानी असुरक्षित पाया जाए, तो हम हिंदी में सूचना देते हैं "
        "और ठीक होने तक मामले पर नज़र रखते हैं।\n\nजुड़ने के लिए गाँव के पोस्टर का QR कोड स्कैन करें, या नीचे गाँव चुनें।\n"
        "/status गाँव के पानी की स्थिति · /stop सदस्यता बंद करें")


def _ok(body: str = "ok"):
    return {"statusCode": 200, "body": body}


def _authorised(event) -> bool:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    supplied = headers.get("x-telegram-bot-api-secret-token", "")
    return hmac.compare_digest(supplied, config.secret(config.SSM_WEBHOOK_SECRET))


def _consent(chat_id: int, role: str, key: str, label: str) -> None:
    who = "गाँव" if role == "v" else "ब्लॉक (इंजीनियर)"
    text = (f"<b>{label}</b> के {who} की सूचनाएं पाने के लिए आपकी अनुमति चाहिए।\n"
            "हम सिर्फ़ आपकी Telegram चैट आईडी और चुना गया गाँव या ब्लॉक रखेंगे। /stop से कभी भी हटा सकते हैं।")
    telegram.send_message(chat_id, text, [[("✅ हाँ", f"s:{role}:{key}:y"), ("❌ नहीं", f"s:{role}:{key}:n")]])


def _village_picker(chat_id: int) -> None:
    villages = sorted(store.list_villages(),
                      key=lambda v: (v.get("source") != "fixtures", v.get("district") or "", v.get("name") or ""))[:12]
    rows = [[(f"{v['name']} ({v.get('block') or v.get('district')})", f"j:{v['key']}")] for v in villages]
    telegram.send_message(chat_id, HELP, rows or None)


def _status(chat_id: int) -> None:
    subs = store.chat_subscriptions(chat_id)
    if not subs:
        telegram.send_message(chat_id, "आप अभी किसी गाँव से नहीं जुड़े हैं। /start से जुड़ें।")
        return
    lines = []
    for s in subs:
        kind, key = s["scope_pk"].split("#", 1)
        if kind == "VILLAGE" and (b := views.village_bundle(key)):
            lines.append(f"• <b>{b['village']['name']}</b>: {b['status_text']['hi']}")
        elif kind == "BLOCK":
            open_cases = [c for c in store.block_cases(key) if c.get("status") in store.OPEN_STATUSES]
            lines.append(f"• ब्लॉक {key}: {len(open_cases)} खुले मामले")
    telegram.send_message(chat_id, "\n".join(lines))


def _command(u: dict) -> None:
    chat, cmd, arg = u["chat_id"], u["command"], u.get("arg", "")
    if cmd == "/start" and arg[:2] in ("v_", "e_"):
        role, key = arg[0], arg[2:]
        if role == "v":
            v = store.get_village(key)
            if not v:
                telegram.send_message(chat, "यह गाँव हमारे रिकॉर्ड में नहीं मिला।")
                return
            _consent(chat, "v", key, v["name"])
        else:
            _consent(chat, "e", key, f"ब्लॉक {key}")
    elif cmd in ("/start", "/help"):
        _village_picker(chat)
    elif cmd == "/status":
        _status(chat)
    elif cmd == "/stop":
        n = store.unsubscribe_all(chat)
        telegram.send_message(chat, f"आपकी {n} सदस्यता और जानकारी हटा दी गई। धन्यवाद।")
    else:
        telegram.send_message(chat, HELP)


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
    telegram.send_message(u["chat_id"], vision.hint_message(hint))


def _callback(u: dict) -> None:
    chat, data, cb = u["chat_id"], u["data"], u["callback_id"]
    actor = f"tg:{chat}"
    parts = data.split(":")
    try:
        if parts[0] == "j" and len(parts) == 2:
            v = store.get_village(parts[1])
            telegram.answer_callback(cb)
            if v:
                _consent(chat, "v", v["key"], v["name"])
        elif parts[0] == "s" and len(parts) == 4:
            role, key, yes = parts[1], parts[2], parts[3] == "y"
            telegram.clear_buttons(chat, u["message_id"])
            if not yes:
                store.unsubscribe_all(chat)
                telegram.answer_callback(cb, "ठीक है, कुछ भी सेव नहीं किया गया।")
                return
            scope = f"VILLAGE#{key}" if role == "v" else f"BLOCK#{key}"
            store.subscribe(chat, "relay" if role == "v" else "engineer", scope, u.get("name"))
            telegram.answer_callback(cb, "जुड़ गए ✅")
            if role == "v":
                bundle = views.village_bundle(key)
                telegram.send_message(chat, f"✅ आप <b>{bundle['village']['name']}</b> से जुड़ गए।\nअभी की स्थिति: {bundle['status_text']['hi']}")
                for c in bundle["cases"]:
                    if c["status"] in store.OPEN_STATUSES:
                        case = store.get_case(c["case_id"])
                        case_steps.send_alert(case, [chat])
                        case_steps.catch_up_relay(chat, case)
            else:
                telegram.send_message(chat, "✅ आप इंजीनियर के रूप में जुड़ गए। खुले मामलों के कार्ड नीचे हैं; नए मामले भी यहीं आएंगे।")
                if not case_steps.catch_up_engineer(chat, key):
                    telegram.send_message(chat, "इस ब्लॉक में अभी कोई खुला मामला नहीं है।")
        elif parts[0] == "f" and len(parts) == 3:
            case_id = actions.case_for_short(parts[1], "fix")
            actions.log_fix(case_id, parts[2], actor)
            telegram.clear_buttons(chat, u["message_id"])
            telegram.answer_callback(cb, "दर्ज हो गया ✅")
            telegram.send_message(chat, f"✅ दर्ज: {actions.FIX_ACTIONS[parts[2]]}। अब गाँव में दोबारा जांच होगी।")
        elif parts[0] == "x" and len(parts) == 2:
            d = actions.try_close(parts[1], actor)
            msg = ("केस बंद नहीं हो सकता: सिर्फ़ लैब की पास जांच से ही केस बंद होता है।" if not d["allowed"] else "केस बंद करने की अनुमति है।")
            telegram.answer_callback(cb, msg, alert=True)
        elif parts[0] == "k" and len(parts) == 3:
            case_id = actions.case_for_short(parts[1], "kit")
            if config.kit_photo_required() and not store.has_pending_photo(chat):
                telegram.answer_callback(cb, "पहले शीशी की फ़ोटो भेजें, फिर बटन दबाएं।", alert=True)
                return
            actions.require_waiting(case_id, "kit")  # fail before the photo is consumed
            photo, hint = _store_kit_photo(chat, case_id)
            actions.kit_result(case_id, parts[2], actor, photo, hint)
            telegram.clear_buttons(chat, u["message_id"])
            telegram.answer_callback(cb, "नतीजा दर्ज ✅")
        else:
            telegram.answer_callback(cb)
    except actions.ActionError as exc:
        telegram.answer_callback(cb, str(exc), alert=True)


def handler(event, context=None):
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
        elif u["kind"] == "text":
            telegram.send_message(u["chat_id"], HELP)
    except Exception:  # noqa: BLE001 - always 200 so Telegram doesn't retry forever
        log.exception("webhook handling failed")
    return _ok()
