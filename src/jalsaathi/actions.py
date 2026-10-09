"""Things people do to a case. Shared by the Telegram webhook and the admin API so both take the same path."""

from __future__ import annotations

import json

from . import config, policy, store

FIX_ACTIONS = {"chlorination": "क्लोरीनेशन", "repair": "मरम्मत", "source_changed": "स्रोत बदला", "need_help": "मदद चाहिए"}


class ActionError(Exception):
    pass


def _resume(case_id: str, kind: str, output: dict) -> None:
    tok = store.token_for_case(case_id, kind)
    if not tok:
        raise ActionError(f"this case is not waiting for '{kind}' right now")
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
    store.add_event(case_id, "fix_logged", actor=actor, action=action, note=FIX_ACTIONS[action])
    if action != "need_help":
        _resume(case_id, "fix", {"action": action})


def try_close(case_id: str, actor: str, role: str = "engineer") -> dict:
    """Someone asks to close the case without lab evidence. Cedar decides (it denies) and the timeline records it."""
    d = policy.decide(role, "close_case", case_id, {"evidence": "engineer_says_fixed"})
    store.add_event(case_id, "policy", actor=actor, decision="allow" if d["allowed"] else "deny", action="close_case",
                    policies=d["policies"], reason=d["reason"])
    return d


def kit_result(case_id: str, result: str, actor: str, photo_key: str | None) -> None:
    if result not in ("clean", "contaminated"):
        raise ActionError(f"unknown kit result: {result}")
    store.add_event(case_id, "kit_result", actor=actor, result=result, photo_key=photo_key,
                    note="field-kit H2S vial: " + ("yellow (clean)" if result == "clean" else "black (contaminated)"))
    _resume(case_id, "kit", {"result": result})


def lab_result(case_id: str, result: str, actor: str, simulated: bool) -> None:
    if result not in ("pass", "fail"):
        raise ActionError(f"unknown lab result: {result}")
    note = ("SIMULATED lab re-test (demo control)" if simulated else "lab re-test") + f": {result}"
    store.add_event(case_id, "lab_result", actor=actor, result=result, note=note, simulated=simulated)
    _resume(case_id, "lab", {"result": result})
