"""Cedar policy decisions (DECISIONS.md D-08). Fails closed: any evaluation error is a deny."""

from __future__ import annotations

import re
from functools import lru_cache

from . import metrics, paths

_ID = re.compile(r'@id\("([^"]+)"\)')


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


def _decide(role: str, action: str, case_id: str, context: dict) -> dict:
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
