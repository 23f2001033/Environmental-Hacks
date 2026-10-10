"""Cedar policy decisions (DECISIONS.md D-08, D-33). Fails closed: any evaluation error is a deny.

Decisions go to Amazon Verified Permissions (the same policies, from policies/case.cedar, loaded into a policy store by
the CDK stack) when AVP_POLICY_STORE_ID is set; the local Cedar engine (cedarpy) answers if the service can't be
reached, and in tests. Either way the result says which engine decided.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

from . import metrics, paths

_ID = re.compile(r'@id\("([^"]+)"\)')
_STATEMENT = re.compile(r'@id\("([^"]+)"\)\s*\n((?:permit|forbid)\b.*?;)', re.S)


def statements(text: str | None = None) -> list[tuple[str, str]]:
    """[(id, statement)] from case.cedar, one per policy; the stack loads each into Verified Permissions."""
    text = text if text is not None else paths.policies_file("case.cedar").read_text(encoding="utf-8")
    return [(pid, body.strip()) for pid, body in _STATEMENT.findall(text)]


@lru_cache(maxsize=1)
def _policies() -> tuple[str, list[str]]:
    text = paths.policies_file("case.cedar").read_text(encoding="utf-8")
    return text, _ID.findall(text)  # cedarpy names policies policy0, policy1... in file order


def _named(reasons: list[str], ids: list[str]) -> list[str]:
    out = []
    for r in reasons:
        m = re.fullmatch(r"policy(\d+)", r)
        out.append(ids[int(m.group(1))] if m and int(m.group(1)) < len(ids) else r)
    return out


def _avp_value(value):
    """A Python context value as a Verified Permissions attribute value."""
    if isinstance(value, bool):
        return {"boolean": value}
    if isinstance(value, int):
        return {"long": value}
    if isinstance(value, (list, tuple, set)):
        return {"set": [_avp_value(v) for v in value]}
    if isinstance(value, dict):
        return {"record": {k: _avp_value(v) for k, v in value.items()}}
    return {"string": str(value)}


@lru_cache(maxsize=1)
def _avp_names(store_id: str) -> dict[str, str]:
    """policyId -> our @id (kept in each policy's description)."""
    from . import config

    names, token = {}, None
    while True:
        kwargs = {"policyStoreId": store_id, **({"nextToken": token} if token else {})}
        resp = config.client("verifiedpermissions").list_policies(**kwargs)
        for p in resp.get("policies", []):
            names[p["policyId"]] = (p.get("definition", {}).get("static", {}) or {}).get("description") or p["policyId"]
        token = resp.get("nextToken")
        if not token:
            return names


def _decide_avp(store_id: str, role: str, action: str, case_id: str, context: dict) -> dict:
    from . import config

    resp = config.client("verifiedpermissions").is_authorized(
        policyStoreId=store_id,
        principal={"entityType": "Role", "entityId": role},
        action={"actionType": "Action", "actionId": action},
        resource={"entityType": "Case", "entityId": case_id[:200]},
        context={"contextMap": {k: _avp_value(v) for k, v in context.items()}})
    names = _avp_names(store_id)
    policies = [names.get(p["policyId"], p["policyId"]) for p in resp.get("determiningPolicies", [])]
    errors = [e.get("errorDescription", "") for e in resp.get("errors", [])]
    base = {"action": action, "policies": policies, "engine": "verified-permissions"}
    if errors:
        return {**base, "allowed": False, "reason": "evaluation error, denied (fail closed): " + errors[0]}
    if resp["decision"] == "ALLOW":
        return {**base, "allowed": True, "reason": "permitted by " + ", ".join(policies)}
    return {**base, "allowed": False, "reason": ("forbidden by " + ", ".join(policies)) if policies else "no policy permits this"}


def _decide(role: str, action: str, case_id: str, context: dict) -> dict:
    """Verified Permissions when configured, the local engine otherwise or if it fails. Never raises."""
    store_id = os.environ.get("AVP_POLICY_STORE_ID")
    if store_id:
        try:
            return _decide_avp(store_id, role, action, case_id, context)
        except Exception:  # noqa: BLE001 - the local engine evaluates the very same policies
            pass
    return {**_decide_local(role, action, case_id, context), "engine": "local" if not store_id else "local-fallback"}


def _decide_local(role: str, action: str, case_id: str, context: dict) -> dict:
    """Return {'allowed', 'action', 'policies', 'reason'}. Never raises."""
    try:
        import cedarpy

        text, ids = _policies()
        request = {
            "principal": f'Role::"{role}"',
            "action": f'Action::"{action}"',
            "resource": f'Case::"{case_id}"',
            "context": context,
        }
        result = cedarpy.is_authorized(request, text, [])
        errors = list(result.diagnostics.errors)
        policies = _named(list(result.diagnostics.reasons), ids)
        if errors:
            return {"allowed": False, "action": action, "policies": policies, "reason": "evaluation error, denied (fail closed): " + errors[0]}
        if result.allowed:
            return {"allowed": True, "action": action, "policies": policies, "reason": "permitted by " + ", ".join(policies)}
        reason = ("forbidden by " + ", ".join(policies)) if policies else "no policy permits this"
        return {"allowed": False, "action": action, "policies": policies, "reason": reason}
    except Exception as exc:  # noqa: BLE001 - fail closed on anything unexpected
        return {"allowed": False, "action": action, "policies": [], "reason": f"policy engine error, denied (fail closed): {exc}"}


def decide(role: str, action: str, case_id: str, context: dict) -> dict:
    """Cedar's decision for one action (see _decide), counted on the dashboard by action and outcome."""
    d = _decide(role, action, case_id, context)
    metrics.emit("CedarDecisions", Action=action, Decision="allow" if d["allowed"] else "deny")
    return d
