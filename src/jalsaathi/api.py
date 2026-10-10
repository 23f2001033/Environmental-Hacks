"""Web API (API Gateway HTTP API, payload v2). Contract: docs/API.md. Version prefix /api/v1 is stable."""

from __future__ import annotations

import base64
import hmac
import json
import logging
import statistics
from datetime import datetime
from functools import lru_cache

from . import __version__, actions, app_api, config, links, paths, store, views, webpush

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


def alert_latency(cases: list[dict]) -> dict | None:
    """Seconds from case opened (failed test found) to village warned, over cases that have been warned."""
    secs = sorted((datetime.fromisoformat(c["warned_at"]) - datetime.fromisoformat(c["opened_at"])).total_seconds()
                  for c in cases if c.get("warned_at") and c.get("opened_at"))
    if not secs:
        return None
    return {"cases": len(secs), "median_s": round(statistics.median(secs), 1),
            "p95_s": round(secs[min(len(secs) - 1, int(0.95 * len(secs)))], 1), "max_s": round(secs[-1], 1)}


def _scale_status(run: dict | None) -> dict | None:
    arn = (run or {}).get("scale_execution_arn")
    if not arn:
        return None
    sfn = config.client("stepfunctions")
    ex = sfn.describe_execution(executionArn=arn)
    out = {"status": ex["status"], "started": ex["startDate"].isoformat()}
    if ex.get("stopDate"):
        out.update(stopped=ex["stopDate"].isoformat(), seconds=round((ex["stopDate"] - ex["startDate"]).total_seconds(), 1))
    runs = sfn.list_map_runs(executionArn=arn).get("mapRuns", [])
    if runs:
        counts = sfn.describe_map_run(mapRunArn=runs[0]["mapRunArn"])["itemCounts"]
        out["items"] = {k: counts.get(k) for k in ("total", "succeeded", "failed", "running", "pending")}
    return out


@lru_cache(maxsize=1)
def repeat_failures() -> dict | None:
    try:
        data = json.loads(paths.analysis_file("repeat_failures.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return {k: data.get(k) for k in ("question", "source", "totals", "caveats", "by_state_and_parameter")}


def _stats():
    cases = store.list_cases()
    open_cases = [c for c in cases if c.get("status") in store.OPEN_STATUSES]
    count = lambda key, items: {k: sum(1 for c in items if c.get(key) == k) for k in sorted({c.get(key) for c in items})}
    run = {k: v for k, v in (store.latest_run() or {}).items() if k not in ("pk", "sk", "type")} or None
    try:
        scale = _scale_status(store.latest_run(scale_only=True))
    except Exception as exc:  # noqa: BLE001 - stats must still load
        log.warning("scale status failed: %s", exc)
        scale = None
    villages = store.list_villages()
    return {"villages": len(villages), "villages_on_map": sum(1 for v in villages if v.get("lat") is not None),
            "cases": len(cases), "open_cases": len(open_cases),
            "closed_cases": sum(1 for c in cases if c.get("status") == "CLOSED"),
            "open_by_severity": count("severity", open_cases), "open_by_code": count("code", open_cases),
            "by_status": count("status", cases), "by_source": count("source", cases),
            "alert_latency": alert_latency(cases), "last_run": run, "scale_run": scale,
            "repeat_failures": repeat_failures()}


@lru_cache(maxsize=1)
def _map_key() -> str | None:
    name = config.map_key_name()
    if not name:
        return None
    return config.client("location").describe_key(KeyName=name)["Key"]


def _config():
    try:
        key = _map_key()
    except Exception as exc:  # noqa: BLE001 - the page works without a map
        log.warning("map key lookup failed: %s", exc)
        key = None
    style = (f"https://maps.geo.{config.REGION}.amazonaws.com/v2/styles/Standard/descriptor?key={key}&color-scheme=Light"
             if key else None)
    return {"bot": config.bot_username(), "demo_clock": config.demo_clock(),
            "map": {"style_url": style, "provider": "Amazon Location Service", "center": [78.5, 26.5], "zoom": 5},
            "push": {"vapid_public_key": webpush.public_key()}}


def _admin_route(method: str, path: str, body: dict):
    if path in ("/api/v1/admin/ingest", "/api/v1/admin/scale-run", "/api/v1/admin/reset", "/api/v1/admin/restart-demo"):
        if path.endswith("/reset"):
            payload = {"action": "reset"}
        elif path.endswith("/restart-demo"):
            payload = {"action": "restart_demo"}
        elif path.endswith("/scale-run"):
            payload = {"source": "snapshot", "scale": True}
        else:
            payload = {"source": body.get("source", "fixtures"), "start_cases": body.get("start_cases", True),
                       "villages": body.get("villages")}
        if payload.get("source") not in (None, "fixtures", "snapshot", "live"):
            return _resp(400, {"error": "source must be fixtures, snapshot or live"})
        config.client("lambda").invoke(FunctionName=config.env("INGEST_FUNCTION"), InvocationType="Event",
                                       Payload=json.dumps(payload).encode())
        return _resp(202, {"started": True, "request": payload})
    if path == "/api/v1/admin/links":
        role, key = body.get("role"), str(body.get("key") or "")
        if role not in links.ROLES or not key:
            return _resp(400, {"error": "role must be v (relay) or e (engineer), with a village or block key"})
        return _resp(200, {"role": links.ROLES[role], "key": key, "url": links.url(role, key)})
    case_id = body.get("case_id", "")
    case = store.get_case(case_id)
    if not case:
        return _resp(404, {"error": "case not found"})
    if path == "/api/v1/admin/restart-case":
        import uuid

        config.client("stepfunctions").start_execution(
            stateMachineArn=config.state_machine_arn(), name=f"{case_id}-r{uuid.uuid4().hex[:6]}"[:80],
            input=json.dumps({"case_id": case_id, "timers": case["timers"]}))
        store.add_event(case_id, "restarted", actor="admin-console", note="workflow restarted")
        return _resp(202, {"restarted": True})
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
        if len(parts) > 3:
            try:
                result = app_api.route(method, parts, _body(event) if method == "POST" else {},
                                       event.get("queryStringParameters") or {})
            except app_api.AppError as exc:
                return _resp(exc.status, {"error": str(exc)})
            except actions.ActionError as exc:
                return _resp(409, {"error": str(exc)})
            if result is not None:
                return _resp(200, result)
        if method != "GET":
            return _resp(405, {"error": "method not allowed"})
        if path == "/api/v1/health":
            return _resp(200, {"ok": True, "version": __version__, "demo_clock": config.demo_clock(),
                               "bot": config.bot_username()})
        if path == "/api/v1/config":
            return _resp(200, _config())
        if path == "/api/v1/villages":
            return _resp(200, {"villages": _villages()})
        if len(parts) == 5 and parts[3] == "villages":
            bundle = views.village_bundle(parts[4], make_audio=True)
            return _resp(200, app_api.village_extras(bundle)) if bundle else _resp(404, {"error": "village not found"})
        if len(parts) == 6 and parts[3] == "blocks" and parts[5] == "cases":
            cases = [views.case_view(c, with_timeline=True)
                     for c in store.block_cases(parts[4])]
            return _resp(200, {"block_key": parts[4], "block": cases[0]["block"] if cases else None, "cases": cases,
                               "links": {"engineer_join": config.join_link("e", parts[4]),
                                         "app_page": f"{config.public_base()}/app/engineer/{parts[4]}"}})
        if len(parts) == 5 and parts[3] == "cases":
            case = store.get_case(parts[4])
            return _resp(200, views.case_view(case)) if case else _resp(404, {"error": "case not found"})
        if path == "/api/v1/stats":
            return _resp(200, _stats())
        return _resp(404, {"error": "not found"})
    except Exception:  # noqa: BLE001
        log.exception("api error")
        return _resp(500, {"error": "internal error"})
