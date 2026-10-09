"""DynamoDB single-table access (docs/BUILD_PLAN.md section 4). All numbers cross the boundary as Decimal."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal

from . import config

OPEN_STATUSES = {"DETECTED", "WARNED", "AWAITING_FIX", "ESCALATED", "AWAITING_RETEST", "PROVISIONALLY_SAFE"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_ddb(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_ddb(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [to_ddb(v) for v in value]
    return value


def from_ddb(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: from_ddb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_ddb(v) for v in value]
    return value


def _t():
    return config.table()


def _conditional_put(item: dict) -> bool:
    from botocore.exceptions import ClientError

    try:
        _t().put_item(Item=to_ddb(item), ConditionExpression="attribute_not_exists(pk)")
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def _query(pk: str, prefix: str | None = None, index: str | None = None) -> list[dict]:
    from boto3.dynamodb.conditions import Key

    key_pk, key_sk = ("gsi1pk", "gsi1sk") if index else ("pk", "sk")
    cond = Key(key_pk).eq(pk)
    if prefix:
        cond = cond & Key(key_sk).begins_with(prefix)
    kwargs = {"KeyConditionExpression": cond}
    if index:
        kwargs["IndexName"] = index
    items, start = [], None
    while True:
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = _t().query(**kwargs)
        items += resp.get("Items", [])
        start = resp.get("LastEvaluatedKey")
        if not start:
            return [from_ddb(i) for i in items]


def _get(pk: str, sk: str) -> dict | None:
    item = _t().get_item(Key={"pk": pk, "sk": sk}).get("Item")
    return from_ddb(item) if item else None


# Villages and samples

def put_village(v: dict) -> None:
    _t().put_item(Item=to_ddb({"pk": f"VILLAGE#{v['key']}", "sk": "META", "type": "village", **v}))


def get_village(key: str) -> dict | None:
    return _get(f"VILLAGE#{key}", "META")


def put_sample(village_key: str, s: dict) -> bool:
    sid = s.get("sample_id") or f"{s.get('parameter')}-{s.get('lab_approval')}"
    item = {"pk": f"VILLAGE#{village_key}", "sk": f"SAMPLE#{s.get('lab_approval') or 'unknown'}#{sid}", "type": "sample", **s}
    return _conditional_put(item)


def village_items(key: str) -> list[dict]:
    return _query(f"VILLAGE#{key}")


def list_villages() -> list[dict]:
    from boto3.dynamodb.conditions import Attr

    items, start = [], None
    while True:
        kwargs = {"FilterExpression": Attr("type").eq("village")}
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = _t().scan(**kwargs)
        items += resp.get("Items", [])
        start = resp.get("LastEvaluatedKey")
        if not start:
            return [from_ddb(i) for i in items]


# Cases

def create_case(case: dict) -> bool:
    item = {"pk": f"CASE#{case['case_id']}", "sk": "META", "type": "case",
            "gsi1pk": f"BLOCK#{case['block_key']}", "gsi1sk": f"{case['status']}#{case['opened_at']}", **case}
    created = _conditional_put(item)
    if created:
        _t().put_item(Item={"pk": f"VILLAGE#{case['village_key']}", "sk": f"CASEREF#{case['case_id']}", "type": "caseref",
                            "case_id": case["case_id"]})
    return created


def get_case(case_id: str) -> dict | None:
    return _get(f"CASE#{case_id}", "META")


def update_case(case_id: str, **fields) -> None:
    fields = dict(fields)
    if "status" in fields:
        current = get_case(case_id) or {}
        fields["gsi1sk"] = f"{fields['status']}#{current.get('opened_at', '')}"
    fields["updated_at"] = now_iso()
    names = {f"#{k}": k for k in fields}
    values = {f":{k}": to_ddb(v) for k, v in fields.items()}
    _t().update_item(Key={"pk": f"CASE#{case_id}", "sk": "META"},
                     UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in fields),
                     ExpressionAttributeNames=names, ExpressionAttributeValues=values)


def add_event(case_id: str, kind: str, actor: str = "system", **details) -> dict:
    ts = now_iso()
    item = {"pk": f"CASE#{case_id}", "sk": f"EVT#{time.time_ns():020d}", "type": "event",
            "kind": kind, "actor": actor, "at": ts, **details}
    _t().put_item(Item=to_ddb(item))
    return item


def events(case_id: str) -> list[dict]:
    return _query(f"CASE#{case_id}", "EVT#")


def block_cases(block_key: str) -> list[dict]:
    return _query(f"BLOCK#{block_key}", index="gsi1")


def list_cases() -> list[dict]:
    from boto3.dynamodb.conditions import Attr

    items, start = [], None
    while True:
        kwargs = {"FilterExpression": Attr("type").eq("case")}
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = _t().scan(**kwargs)
        items += resp.get("Items", [])
        start = resp.get("LastEvaluatedKey")
        if not start:
            return [from_ddb(i) for i in items]


# Step Functions task tokens behind Telegram buttons and admin actions

def put_token(short: str, case_id: str, kind: str, token: str, days: int = 14) -> None:
    ttl = int(time.time()) + days * 86400
    _t().put_item(Item={"pk": f"TOK#{short}", "sk": "META", "type": "token", "case_id": case_id, "kind": kind,
                        "token": token, "ttl": ttl})
    _t().put_item(Item={"pk": f"CASE#{case_id}", "sk": f"TOKREF#{kind}", "type": "tokref", "short": short, "ttl": ttl})


def get_token(short: str) -> dict | None:
    return _get(f"TOK#{short}", "META")


def token_for_case(case_id: str, kind: str) -> dict | None:
    ref = _get(f"CASE#{case_id}", f"TOKREF#{kind}")
    return get_token(ref["short"]) if ref else None


def delete_token(short: str, case_id: str, kind: str) -> None:
    _t().delete_item(Key={"pk": f"TOK#{short}", "sk": "META"})
    _t().delete_item(Key={"pk": f"CASE#{case_id}", "sk": f"TOKREF#{kind}"})


# Telegram subscribers

def subscribe(chat_id: int, role: str, scope_pk: str, name: str | None = None) -> None:
    at = now_iso()
    _t().put_item(Item={"pk": scope_pk, "sk": f"SUB#tg{chat_id}", "type": "sub", "chat_id": chat_id, "role": role,
                        "consent_at": at})
    _t().put_item(Item={"pk": f"CHAT#tg{chat_id}", "sk": f"SUB#{scope_pk}", "type": "chatsub", "role": role,
                        "scope_pk": scope_pk, "name": name or "", "consent_at": at})


def subscribers(scope_pk: str) -> list[dict]:
    return _query(scope_pk, "SUB#")


def chat_subscriptions(chat_id: int) -> list[dict]:
    return _query(f"CHAT#tg{chat_id}", "SUB#")


def unsubscribe_all(chat_id: int) -> int:
    subs = chat_subscriptions(chat_id)
    for s in subs:
        _t().delete_item(Key={"pk": s["scope_pk"], "sk": f"SUB#tg{chat_id}"})
        _t().delete_item(Key={"pk": f"CHAT#tg{chat_id}", "sk": s["sk"]})
    _t().delete_item(Key={"pk": f"CHAT#tg{chat_id}", "sk": "PHOTO"})
    return len(subs)


def seen_update(update_id: int) -> bool:
    """True if this Telegram update was already handled (de-duplication)."""
    return not _conditional_put({"pk": f"UPD#{update_id}", "sk": "META", "type": "upd", "ttl": int(time.time()) + 2 * 86400})


def put_pending_photo(chat_id: int, file_id: str) -> None:
    _t().put_item(Item={"pk": f"CHAT#tg{chat_id}", "sk": "PHOTO", "type": "photo", "file_id": file_id,
                        "at": now_iso(), "ttl": int(time.time()) + 86400})


def pop_pending_photo(chat_id: int) -> str | None:
    item = _get(f"CHAT#tg{chat_id}", "PHOTO")
    if item:
        _t().delete_item(Key={"pk": f"CHAT#tg{chat_id}", "sk": "PHOTO"})
        return item["file_id"]
    return None


# Runs and demo reset

def put_run(run: dict) -> None:
    _t().put_item(Item=to_ddb({"pk": f"RUN#{run['run_id']}", "sk": "META", "type": "run", **run}))


def latest_run() -> dict | None:
    from boto3.dynamodb.conditions import Attr

    items, start = [], None
    while True:
        kwargs = {"FilterExpression": Attr("type").eq("run")}
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = _t().scan(**kwargs)
        items += resp.get("Items", [])
        start = resp.get("LastEvaluatedKey")
        if not start:
            break
    items = [from_ddb(i) for i in items]
    return max(items, key=lambda r: r.get("finished_at", ""), default=None)


def reset_demo() -> int:
    """Delete cases, samples, villages, events, tokens and runs. Keeps subscriptions so demo phones stay joined."""
    keep = {"sub", "chatsub"}
    deleted, start = 0, None
    while True:
        kwargs = {"ProjectionExpression": "pk, sk, #t", "ExpressionAttributeNames": {"#t": "type"}}
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = _t().scan(**kwargs)
        with _t().batch_writer() as batch:
            for item in resp.get("Items", []):
                if item.get("type") not in keep:
                    batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                    deleted += 1
        start = resp.get("LastEvaluatedKey")
        if not start:
            return deleted
