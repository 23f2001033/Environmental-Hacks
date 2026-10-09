"""Web API (API Gateway HTTP API, payload v2). Contract: docs/API.md. Version prefix /api/v1 is stable."""

from __future__ import annotations

import base64
import hmac
import json
import logging

from . import __version__, actions, config, store, views

log = logging.getLogger()
log.setLevel(logging.INFO)

HEADERS = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
           "Access-Control-Allow-Origin": "*"}


def _resp(status: int, body) -> dict:
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body, ensure_ascii=False, default=str)}


def _body(event) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _admin(event) -> bool:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    return hmac.compare_digest(headers.get("x-admin-token", ""), config.secret(config.SSM_CONSOLE_TOKEN))


def _villages():
    cases = store.list_cases()
    by_village: dict[str, list] = {}
    for c in cases:
        by_village.setdefault(c["village_key"], []).append(c)
    out = [views.village_summary(v, by_village.get(v["key"], [])) for v in store.list_villages()]
    return sorted(out, key=lambda s: (s["status"] != "unsafe", s.get("district") or "", s.get("name") or ""))


def _stats():
    cases = store.list_cases()
    open_cases = [c for c in cases if c.get("status") in store.OPEN_STATUSES]
    count = lambda key, items: {k: sum(1 for c in items if c.get(key) == k) for k in sorted({c.get(key) for c in items})}
    return {"villages": len(store.list_villages()), "cases": len(cases), "open_cases": len(open_cases),
            "closed_cases": sum(1 for c in cases if c.get("status") == "CLOSED"),
            "open_by_severity": count("severity", open_cases), "open_by_code": count("code", open_cases),
            "by_status": count("status", cases), "last_run": store.latest_run()}


def _admin_route(method: str, path: str, body: dict):
    if path == "/api/v1/admin/ingest":
        payload = {"source": body.get("source", "fixtures"), "start_cases": body.get("start_cases", True),
                   "villages": body.get("villages")}
        config.client("lambda").invoke(FunctionName=config.env("INGEST_FUNCTION"), InvocationType="Event",
                                       Payload=json.dumps(payload).encode())
        return _resp(202, {"started": True, "request": payload})
    if path == "/api/v1/admin/reset":
        return _resp(200, {"deleted": store.reset_demo()})
    case_id = body.get("case_id", "")
    if not store.get_case(case_id):
        return _resp(404, {"error": "case not found"})
    try:
        if path == "/api/v1/admin/engineer-action":
            actions.log_fix(case_id, body.get("action", "chlorination"), "admin-console (demo)")
            return _resp(200, {"ok": True})
        if path == "/api/v1/admin/try-close":
            return _resp(200, actions.try_close(case_id, "admin-console (demo)"))
        if path == "/api/v1/admin/kit-result":
            actions.kit_result(case_id, body.get("result", "clean"), "admin-console (demo)", None)
            return _resp(200, {"ok": True})
        if path == "/api/v1/admin/lab-result":
            actions.lab_result(case_id, body.get("result", "pass"), "admin-console (demo)", simulated=True)
            return _resp(200, {"ok": True})
    except actions.ActionError as exc:
        return _resp(409, {"error": str(exc)})
    return _resp(404, {"error": "not found"})


def handler(event, context=None):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = (event.get("rawPath") or "/").rstrip("/")
    parts = path.split("/")
    try:
        if method == "OPTIONS":
            return _resp(204, {})
        if path.startswith("/api/v1/admin/"):
            if method != "POST":
                return _resp(405, {"error": "use POST"})
            if not _admin(event):
                return _resp(401, {"error": "admin token required (x-admin-token)"})
            return _admin_route(method, path, _body(event))
        if method != "GET":
            return _resp(405, {"error": "method not allowed"})
        if path == "/api/v1/health":
            return _resp(200, {"ok": True, "version": __version__, "demo_clock": config.demo_clock(),
                               "bot": config.bot_username()})
        if path == "/api/v1/villages":
            return _resp(200, {"villages": _villages()})
        if len(parts) == 5 and parts[3] == "villages":
            bundle = views.village_bundle(parts[4])
            return _resp(200, bundle) if bundle else _resp(404, {"error": "village not found"})
        if len(parts) == 6 and parts[3] == "blocks" and parts[5] == "cases":
            cases = [views.case_view(c, with_timeline=False) for c in store.block_cases(parts[4])]
            return _resp(200, {"block_key": parts[4], "cases": cases, "links": {"engineer_join": config.join_link("e", parts[4])}})
        if len(parts) == 5 and parts[3] == "cases":
            case = store.get_case(parts[4])
            return _resp(200, views.case_view(case)) if case else _resp(404, {"error": "case not found"})
        if path == "/api/v1/stats":
            return _resp(200, _stats())
        return _resp(404, {"error": "not found"})
    except Exception:  # noqa: BLE001
        log.exception("api error")
        return _resp(500, {"error": "internal error"})
