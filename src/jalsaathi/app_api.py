"""Web-app routes: what relays and engineers do in the app, app notifications, and the officials' overview.

Relay and engineer actions need the signed link token `k` (links.py) and go through the same actions module as the
Telegram buttons, so Cedar decides exactly the same way in both channels.
"""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from urllib.parse import urlparse

from . import actions, config, i18n, links, rules, store, vision

log = logging.getLogger()

PUSH_HOSTS = ("fcm.googleapis.com", "push.services.mozilla.com", "notify.windows.com", "push.apple.com")
MAX_PHOTO_BYTES = 6 * 1024 * 1024


class AppError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


@lru_cache(maxsize=1)
def _s3_presigner():
    import boto3
    from botocore.config import Config

    return boto3.client("s3", region_name=config.REGION, endpoint_url=f"https://s3.{config.REGION}.amazonaws.com",
                        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))


def _case_in(scope: str, key: str, case_id: str) -> dict:
    case = store.get_case(case_id or "")
    field = "block_key" if scope == "e" else "village_key"
    if not case or str(case.get(field)) != key:
        raise AppError(404, "case not found here")
    return case


DEMO = "demo"


def _require(role: str, key: str, body: dict, case: dict) -> None:
    """A signed link for this place, or the public demo link, which only works on the 13 demo cases."""
    if body.get("k") == DEMO and case.get("source") == "fixtures":
        return
    if not links.verify(role, key, body.get("k")):
        raise AppError(401, "this link is not valid for this " + ("block" if role == "e" else "village"))


def engineer(block: str, action: str, body: dict) -> dict:
    case = _case_in("e", block, body.get("case_id"))
    _require("e", block, body, case)
    actor = "web app (engineer)"
    if action == "fix":
        actions.log_fix(case["case_id"], body.get("action", ""), actor)
        return {"ok": True}
    if action == "close":
        return actions.try_close(case["case_id"], actor)
    raise AppError(404, "not found")


def relay(village: str, action: str, body: dict) -> dict:
    case = _case_in("v", village, body.get("case_id"))
    _require("v", village, body, case)
    prefix = f"private/kit/{case['case_id']}/"
    if action == "upload":
        actions.require_waiting(case["case_id"], "kit")
        key = f"{prefix}web-{uuid.uuid4().hex[:12]}.jpg"
        url = _s3_presigner().generate_presigned_url(
            "put_object", Params={"Bucket": config.bucket(), "Key": key, "ContentType": "image/jpeg"}, ExpiresIn=300)
        return {"upload_url": url, "photo_key": key}
    photo_key = body.get("photo_key")
    if photo_key is not None and not str(photo_key).startswith(prefix):
        raise AppError(400, "photo does not belong to this case")
    if action == "hint":
        obj = config.client("s3").get_object(Bucket=config.bucket(), Key=photo_key)
        if obj["ContentLength"] > MAX_PHOTO_BYTES:
            raise AppError(400, "photo too large")
        hint = vision.kit_hint(obj["Body"].read())
        store.put_photo_hint(photo_key, hint)
        lang = i18n.norm(body.get("lang"))
        return {"hint": hint, "message": i18n.t(f"hint_{hint['colour']}", lang) if hint else None}
    if action == "kit":
        if config.kit_photo_required() and not photo_key:
            raise AppError(400, "send a photo of the vial first")
        actions.kit_result(case["case_id"], body.get("result", ""), "web app (relay)", photo_key,
                           store.photo_hint(photo_key) if photo_key else None)
        return {"ok": True}
    raise AppError(404, "not found")


def push_subscribe(body: dict) -> dict:
    scope, key, sub = body.get("scope"), str(body.get("key") or ""), body.get("subscription") or {}
    endpoint = sub.get("endpoint", "")
    host = urlparse(endpoint).hostname or ""
    if scope not in ("village", "block") or not key:
        raise AppError(400, "scope must be village or block, with a key")
    if not endpoint.startswith("https://") or not any(host == h or host.endswith("." + h) for h in PUSH_HOSTS):
        raise AppError(400, "not a browser push endpoint")
    if not (sub.get("keys") or {}).get("p256dh") or not sub["keys"].get("auth"):
        raise AppError(400, "subscription keys missing")
    if scope == "village" and not store.get_village(key):
        raise AppError(404, "village not found")
    store.push_subscribe(f"{'VILLAGE' if scope == 'village' else 'BLOCK'}#{key}",
                         {"endpoint": endpoint, "keys": {"p256dh": sub["keys"]["p256dh"], "auth": sub["keys"]["auth"]}},
                         i18n.norm(body.get("lang")))
    return {"subscribed": True}


def activity(limit: int = 40) -> dict:
    """The newest events across all cases, for the officials' view."""
    cache: dict[str, dict | None] = {}
    out = []
    for e in store.feed(min(max(limit, 1), 100)):
        cid = e["case_id"]
        if cid not in cache:
            cache[cid] = store.get_case(cid)
        case = cache[cid]
        if not case:
            continue
        out.append({**{k: e.get(k) for k in ("at", "kind", "actor", "note", "decision", "action", "result", "reason")
                       if e.get(k) is not None},
                    "case_id": cid, "code": case.get("code"), "village": case.get("village"),
                    "village_key": case.get("village_key"), "block": case.get("block"), "block_key": case.get("block_key"),
                    "district": case.get("district"), "state": case.get("state"), "source": case.get("source")})
    return {"events": out}


def overview() -> dict:
    """Districts and blocks for officials: what is open, how bad, and what is overdue."""
    districts: dict[tuple, dict] = {}
    for c in store.list_cases():
        d = districts.setdefault((c.get("state"), c.get("district")), {
            "state": c.get("state"), "district": c.get("district"), "open": 0, "closed": 0, "provisional": 0,
            "escalated": 0, "by_severity": {}, "by_code": {}, "villages": set(), "blocks": {}})
        b = d["blocks"].setdefault(c.get("block_key"), {"block_key": c.get("block_key"), "block": c.get("block"),
                                                        "open": 0, "escalated": 0, "villages": set()})
        status = c.get("status")
        if status == "CLOSED":
            d["closed"] += 1
            continue
        if status not in store.OPEN_STATUSES:
            continue
        overdue = status == "ESCALATED" or int(c.get("escalations") or 0) > 0
        d["open"] += 1
        b["open"] += 1
        d["escalated"] += overdue
        b["escalated"] += overdue
        d["provisional"] += status == "PROVISIONALLY_SAFE"
        d["by_severity"][c.get("severity")] = d["by_severity"].get(c.get("severity"), 0) + 1
        d["by_code"][c.get("code")] = d["by_code"].get(c.get("code"), 0) + 1
        d["villages"].add(c.get("village_key"))
        b["villages"].add(c.get("village_key"))
    rows = []
    for d in districts.values():
        blocks = sorted(({**b, "villages": len(b["villages"])} for b in d["blocks"].values() if b["open"]),
                        key=lambda b: (-b["escalated"], -b["open"]))
        rows.append({**d, "villages": len(d["villages"]), "blocks": blocks,
                     "chemical_share": round(sum(n for code, n in d["by_code"].items()
                                                 if rules.contaminant_class(code) == "chemical") / d["open"], 3)
                     if d["open"] else 0})
    rows.sort(key=lambda d: (-d["escalated"], -d["open"]))
    totals = {k: sum(d[k] for d in rows) for k in ("open", "closed", "provisional", "escalated", "villages")}
    return {"totals": totals, "districts": rows}


def ask(body: dict) -> dict:
    """Ask JalSaathi from the app: the same checked pipeline as the Telegram voice questions (text in, text + voice out)."""
    from . import assistant

    key, question = str(body.get("village") or ""), str(body.get("question") or "").strip()
    if not key or not question:
        raise AppError(400, "village and question are required")
    if len(question) > 300:
        raise AppError(400, "please keep the question under 300 characters")
    lang = i18n.norm(body.get("lang"))
    result = assistant.answer(key, question, lang, actor="web app")
    result["audio_url"] = assistant.speak(result["answer"], lang)
    return {k: result.get(k) for k in ("answer", "audio_url", "lang", "fallback", "question_en", "answer_en", "guardrail",
                                       "cedar", "ms")}


def route(method: str, parts: list[str], body: dict, query: dict) -> dict | None:
    """Returns the response body, or None if the path is not an app route. Raises AppError or ActionError."""
    if method == "POST" and len(parts) == 6 and parts[3] == "engineer":
        return engineer(parts[4], parts[5], body)
    if method == "POST" and len(parts) == 6 and parts[3] == "relay":
        return relay(parts[4], parts[5], body)
    if method == "POST" and parts[3:] == ["ask"]:
        return ask(body)
    if method == "POST" and parts[3:] == ["push", "subscribe"]:
        return push_subscribe(body)
    if method == "GET" and parts[3:] == ["activity"]:
        return activity(int(query.get("limit") or 40))
    if method == "GET" and parts[3:] == ["overview"]:
        return overview()
    if method == "GET" and parts[3:] == ["access"]:
        role, key = query.get("role", ""), query.get("key", "")
        if query.get("k") == DEMO:
            return {"valid": True, "demo": True}  # acts only on demo cases (checked per action)
        return {"valid": role in links.ROLES and links.verify(role, key, query.get("k")), "demo": False}
    return None


def village_extras(bundle: dict) -> dict:
    """Bundle additions for the app: the app links people can open (public ones only)."""
    bundle["links"]["app_page"] = f"{config.public_base()}/?v={bundle['village']['key']}"
    return bundle

