"""Things people do to a case. Shared by the Telegram webhook and the admin API so both take the same path."""

from __future__ import annotations

import json

from . import config, metrics, policy, store

FIX_ACTIONS = {"chlorination": "chlorination (क्लोरीनेशन)", "repair": "repair (मरम्मत)", "source_changed": "source changed (स्रोत बदला)",
               "need_help": "needs help (मदद चाहिए)"}


class ActionError(Exception):
    pass


def require_waiting(case_id: str, kind: str) -> dict:
    """The task token the case is waiting on. Checked before anything is recorded, so a rejected action leaves no trace."""
    tok = store.token_for_case(case_id, kind)
    if not tok:
        raise ActionError(f"this case is not waiting for '{kind}' right now")
    return tok


def _resume(case_id: str, kind: str, tok: dict, output: dict) -> None:
    config.client("stepfunctions").send_task_success(taskToken=tok["token"], output=json.dumps(output))
    store.delete_token(tok["pk"].split("#", 1)[1], case_id, kind)


def case_for_short(short: str, kind: str) -> str:
    tok = store.get_token(short)
    if not tok or tok.get("kind") != kind:
        raise ActionError("this button has expired")
    return tok["case_id"]


def log_fix(case_id: str, action: str, actor: str) -> None:
    if action not in FIX_ACTIONS:
        raise ActionError(f"unknown fix action: {action}")
    tok = require_waiting(case_id, "fix")
    store.add_event(case_id, "fix_logged", actor=actor, action=action, note=FIX_ACTIONS[action])
    if action != "need_help":
        _resume(case_id, "fix", tok, {"action": action})
    metrics.emit("FixesLogged", Action=action)


def try_close(case_id: str, actor: str, role: str = "engineer") -> dict:
    """Someone asks to close the case without lab evidence. Cedar decides (it denies) and the timeline records it."""
    d = policy.decide(role, "close_case", case_id, {"evidence": "engineer_says_fixed"})
    store.add_event(case_id, "policy", actor=actor, decision="allow" if d["allowed"] else "deny", action="close_case",
                    policies=d["policies"], reason=d["reason"])
    return d


def kit_result(case_id: str, result: str, actor: str, photo_key: str | None, ai_hint: dict | None = None) -> None:
    if result not in ("clean", "contaminated"):
        raise ActionError(f"unknown kit result: {result}")
    tok = require_waiting(case_id, "kit")
    note = "field-kit H2S vial: " + ("yellow (clean)" if result == "clean" else "black (contaminated)")
    if ai_hint:
        agrees = {"yellow": "clean", "black": "contaminated"}.get(ai_hint.get("colour")) == result
        note += f"; AI suggestion was {ai_hint.get('colour')} ({ai_hint.get('confidence')}), " + ("agrees" if agrees else "person chose differently")
    store.add_event(case_id, "kit_result", actor=actor, result=result, photo_key=photo_key, ai_hint=ai_hint, note=note)
    _resume(case_id, "kit", tok, {"result": result})
    metrics.emit("FieldTests", Result=result)


def lab_result(case_id: str, result: str, actor: str, simulated: bool) -> None:
    if result not in ("pass", "fail"):
        raise ActionError(f"unknown lab result: {result}")
    tok = require_waiting(case_id, "lab")
    note = ("SIMULATED lab re-test (demo control)" if simulated else "lab re-test") + f": {result}"
    store.add_event(case_id, "lab_result", actor=actor, result=result, note=note, simulated=simulated)
    _resume(case_id, "lab", tok, {"result": result})
    metrics.emit("LabResults", Result=result)
