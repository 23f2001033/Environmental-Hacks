"""App notifications (Web Push) for a village or block, sent next to the Telegram messages. Never blocks a case."""

from __future__ import annotations

import logging
import re

from . import advice, config, i18n, store, webpush

log = logging.getLogger()

GONE = {404, 410}


def _plain(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).replace("\n", " ").strip()


def push(scope_pk: str, key: str, case: dict, url_path: str, **kw) -> int:
    """Send one message (an i18n key) to every app subscriber of the scope, each in their language."""
    sent = 0
    try:
        subs = store.push_subscribers(scope_pk)
    except Exception as exc:  # noqa: BLE001
        log.warning("push subscribers for %s failed: %s", scope_pk, exc)
        return 0
    for s in subs:
        lang = i18n.norm(s.get("lang"))
        body = _plain(i18n.t(key, lang, village=case["village"], found=advice.name(case["code"], lang), **kw))
        message = {"title": "JalSaathi", "body": body, "url": f"{config.public_base()}{url_path}",
                   "tag": f"{case['case_id']}-{key}"}
        try:
            status = webpush.send(s["subscription"], message)
            if status in GONE:
                store.push_unsubscribe(scope_pk, s["sk"])
            sent += status in (200, 201, 202)
        except Exception as exc:  # noqa: BLE001 - one bad subscription must not stop the case
            log.warning("web push to %s failed: %s", s.get("sk"), exc)
    return sent


def village(case: dict, key: str, **kw) -> int:
    return push(f"VILLAGE#{case['village_key']}", key, case, f"/?v={case['village_key']}", **kw)


def block(case: dict, key: str, **kw) -> int:
    return push(f"BLOCK#{case['block_key']}", key, case, f"/app/engineer/{case['block_key']}", **kw)
