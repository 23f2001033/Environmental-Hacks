"""Step Functions task handlers for one case (docs/BUILD_PLAN.md section 5).

Each state invokes this Lambda with {"step": ..., "case_id": ..., "token": <task token, for wait steps>}.
"""

from __future__ import annotations

import logging
import secrets

from . import advice, config, policy, store, telegram, voice

log = logging.getLogger()
log.setLevel(logging.INFO)

FIX_BUTTONS = [
    [("🧪 क्लोरीनेशन किया", "chlorination"), ("🔧 मरम्मत की", "repair")],
    [("🔁 स्रोत बदला", "source_changed"), ("🆘 मदद चाहिए", "need_help")],
]


def _send_safely(chat_id: int, text: str, buttons=None, audio_url: str | None = None) -> bool:
    try:
        telegram.send_message(chat_id, text, buttons)
        if audio_url:
            telegram.send_audio(chat_id, audio_url, title="JalSaathi सूचना")
        return True
    except Exception as exc:  # noqa: BLE001 - one bad chat must not stop the case
        log.warning("telegram send to %s failed: %s", chat_id, exc)
        return False


def _relays(case: dict) -> list[dict]:
    return store.subscribers(f"VILLAGE#{case['village_key']}")


def _engineers(case: dict) -> list[dict]:
    return store.subscribers(f"BLOCK#{case['block_key']}")


def _new_token(case_id: str, kind: str, token: str) -> str:
    short = secrets.token_urlsafe(6)
    store.put_token(short, case_id, kind, token)
    return short


def send_alert(case: dict, chat_ids: list[int] | None = None) -> int:
    """Village alert (text + voice). Used by the workflow and when a relay joins a village with an open case."""
    targets = chat_ids if chat_ids is not None else [s["chat_id"] for s in _relays(case)]
    if not targets:
        return 0
    url = voice.public_url(voice.ensure_audio(case))
    text = advice.alert_text(case, "hi", page_url=config.village_url(case["village_key"]),
                             data_as_of=(case.get("opened_at") or "")[:10])
    return sum(_send_safely(cid, text, audio_url=url) for cid in targets)


def step_init(case: dict, event: dict) -> dict:
    store.add_event(case["case_id"], "detected", note=f"{case.get('parameter')} {case.get('value')} {case.get('unit') or ''}".strip(),
                    source=case.get("source"))
    return {"timers": case["timers"]}


def step_alert(case: dict, event: dict) -> dict:
    decision = policy.decide("system", "send_message", case["case_id"], advice.policy_context(case["code"]))
    store.add_event(case["case_id"], "policy", decision="allow" if decision["allowed"] else "deny",
                    action="send_message", policies=decision["policies"], reason=decision["reason"])
    if not decision["allowed"]:
        store.update_case(case["case_id"], status="WARNED", alert_blocked=True)
        return {"sent": 0, "blocked": True}
    if case.get("source") == "fixtures":
        voice.ensure_audio(case)  # demo villages always have their voice note ready; others get one on first need
    sent = send_alert(case)
    store.update_case(case["case_id"], status="WARNED", warned_at=store.now_iso())
    store.add_event(case["case_id"], "warned", note=f"alert sent to {sent} village contact(s)")
    return {"sent": sent}


def step_await_fix(case: dict, event: dict) -> None:
    short = _new_token(case["case_id"], "fix", event["token"])
    buttons = [[(label, f"f:{short}:{action}") for label, action in row] for row in FIX_BUTTONS]
    buttons.append([("✅ केस बंद करें", f"x:{case['case_id']}")])
    engineers = _engineers(case)
    for e in engineers:
        _send_safely(e["chat_id"], advice.engineer_card(case, "hi"), buttons)
    store.update_case(case["case_id"], status="AWAITING_FIX")
    store.add_event(case["case_id"], "awaiting_fix",
                    note=f"asked {len(engineers)} engineer(s)" if engineers else "no engineer subscribed yet; waiting")


ESCALATION = {
    "fix": ("fix deadline passed", "काम की समय सीमा निकल गई। मामला ज़िले को भेजा गया।", "AWAITING_FIX"),
    "retest": ("field-kit re-test overdue", "दोबारा जांच की समय सीमा निकल गई। कृपया शीशी से जांच करें।", "AWAITING_RETEST"),
    "lab": ("lab re-test overdue", "लैब की दोबारा जांच का इंतज़ार है। मामला ज़िले को भेजा गया।", "PROVISIONALLY_SAFE"),
}


def step_escalate(case: dict, event: dict) -> dict:
    reason = event.get("reason", "fix")
    note, message, status_after = ESCALATION.get(reason, ESCALATION["fix"])
    counts = dict(case.get("escalation_counts") or {})
    counts[reason] = int(counts.get(reason, 0)) + 1
    n = counts[reason]
    store.update_case(case["case_id"], status="ESCALATED" if reason == "fix" else status_after,
                      escalations=sum(counts.values()), escalation_counts=counts)
    store.add_event(case["case_id"], "escalated", note=f"{note} (escalation {n} of 3)")
    targets = _engineers(case) if reason in ("fix", "lab") else _relays(case)
    for t in targets:
        _send_safely(t["chat_id"], f"⏰ <b>{case['village']}</b>: {message}")
    return {"escalations": n}


def step_await_kit(case: dict, event: dict) -> None:
    short = _new_token(case["case_id"], "kit", event["token"])
    text = (f"🧪 <b>{case['village']}</b>: मरम्मत दर्ज हो गई है।\n"
            "H2S शीशी से पानी की जांच करें। 24 से 48 घंटे बाद शीशी की फ़ोटो भेजें, फिर नतीजा चुनें।")
    buttons = [[("⚫ काली (दूषित)", f"k:{short}:contaminated"), ("🟡 पीली (साफ़)", f"k:{short}:clean")]]
    for r in _relays(case):
        _send_safely(r["chat_id"], text, buttons)
    store.update_case(case["case_id"], status="AWAITING_RETEST")
    store.add_event(case["case_id"], "awaiting_retest", note="field-kit re-test requested")


def step_reopen(case: dict, event: dict) -> None:
    store.update_case(case["case_id"], status="AWAITING_FIX")
    store.add_event(case["case_id"], "reopened", note=event.get("reason", "re-test not clean"))
    for r in _relays(case):
        _send_safely(r["chat_id"], f"⚠️ <b>{case['village']}</b>: दोबारा जांच साफ़ नहीं आई। पहले बताई गई सावधानियां जारी रखें।")


def step_provisional(case: dict, event: dict) -> dict:
    d = policy.decide("relay", "mark_provisional", case["case_id"], {"evidence": "kit_clean"})
    store.add_event(case["case_id"], "policy", decision="allow" if d["allowed"] else "deny", action="mark_provisional",
                    policies=d["policies"], reason=d["reason"])
    if d["allowed"]:
        store.update_case(case["case_id"], status="PROVISIONALLY_SAFE")
        for r in _relays(case):
            _send_safely(r["chat_id"], f"🟡 <b>{case['village']}</b>: फील्ड जांच साफ़ आई। लैब जांच की पुष्टि तक सावधानी जारी रखें।")
    return {"allowed": d["allowed"]}


def step_await_lab(case: dict, event: dict) -> None:
    _new_token(case["case_id"], "lab", event["token"])
    store.add_event(case["case_id"], "awaiting_lab", note="lab re-test requested")


def step_close(case: dict, event: dict) -> dict:
    d = policy.decide("system", "close_case", case["case_id"], {"evidence": event.get("evidence", "lab_pass")})
    store.add_event(case["case_id"], "policy", decision="allow" if d["allowed"] else "deny", action="close_case",
                    policies=d["policies"], reason=d["reason"])
    if not d["allowed"]:
        raise RuntimeError("close denied by policy: " + d["reason"])
    store.update_case(case["case_id"], status="CLOSED", closed_at=store.now_iso())
    store.add_event(case["case_id"], "closed", note="lab re-test passed")
    for r in _relays(case):
        _send_safely(r["chat_id"], f"✅ <b>{case['village']}</b>: लैब की दोबारा जांच में पानी सुरक्षित पाया गया।")
    return {"closed": True}


STEPS = {
    "init": step_init, "alert": step_alert, "await_fix": step_await_fix, "escalate": step_escalate,
    "await_kit": step_await_kit, "reopen": step_reopen, "provisional": step_provisional,
    "await_lab": step_await_lab, "close": step_close,
}


def handler(event, context=None):
    case = store.get_case(event["case_id"])
    if not case:
        raise RuntimeError(f"case not found: {event['case_id']}")
    return STEPS[event["step"]](case, event)
