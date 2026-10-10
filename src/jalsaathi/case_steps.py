"""Step Functions task handlers for one case (docs/BUILD_PLAN.md section 5).

Each state invokes this Lambda with {"step": ..., "case_id": ..., "token": <task token, for wait steps>}.
Every message goes out in the language each person chose (Hindi by default).
"""

from __future__ import annotations

import logging
import secrets

from . import advice, config, i18n, policy, rules, store, telegram, voice

log = logging.getLogger()
log.setLevel(logging.INFO)

FIX_ACTION_ROWS = [["chlorination", "repair"], ["source_changed", "need_help"]]


def _send_safely(chat_id: int, text: str, buttons=None, audio_url: str | None = None, lang: str = "hi") -> bool:
    try:
        telegram.send_message(chat_id, text, buttons)
        if audio_url:
            telegram.send_audio(chat_id, audio_url, title=i18n.t("audio_title", lang))
        return True
    except Exception as exc:  # noqa: BLE001 - one bad chat must not stop the case
        log.warning("telegram send to %s failed: %s", chat_id, exc)
        return False


def _tell(chat_id: int, key: str, **kw) -> bool:
    """A one-line message from the i18n table, in this chat's language."""
    return _send_safely(chat_id, i18n.t(key, store.chat_lang(chat_id), **kw))


def _relays(case: dict) -> list[dict]:
    return store.subscribers(f"VILLAGE#{case['village_key']}")


def _engineers(case: dict) -> list[dict]:
    return store.subscribers(f"BLOCK#{case['block_key']}")


def _new_token(case_id: str, kind: str, token: str) -> str:
    short = secrets.token_urlsafe(6)
    store.put_token(short, case_id, kind, token)
    return short


def group_by_advice(cases: list[dict]) -> list[list[dict]]:
    """Open cases of a village, worst first, grouped so that each group shares identical advice."""
    ordered = sorted(cases, key=lambda c: (rules.SEVERITY_ORDER.get(c.get("severity"), 9), -(c.get("value") or 0)))
    groups: list[list[dict]] = []
    for c in ordered:
        group = next((g for g in groups if advice.same_advice(g[0], c)), None)
        if group is None:
            groups.append([c])
        else:
            group.append(c)
    return groups


def send_alert_group(cases: list[dict], chat_ids: list[int], lang: str | None = None) -> int:
    """One alert (text + voice) for cases that share advice. lang=None means each chat's own language."""
    if not chat_ids:
        return 0
    first = cases[0]
    village = store.get_village(first["village_key"]) or {}
    sent = 0
    for chat_id in chat_ids:
        chat_lang = lang or store.chat_lang(chat_id)
        text = advice.alert_text_group(cases, chat_lang, page_url=config.village_url(first["village_key"]),
                                       data_as_of=village.get("data_as_of"))
        switch = [[(i18n.t("switch_to", chat_lang), f"l:{i18n.other(chat_lang)}:{first['village_key']}")]]
        if len(switch[0][0][1]) > 64:
            switch = None  # Telegram callback data is limited to 64 bytes
        url = voice.public_url(voice.ensure_group_audio(cases, chat_lang))
        sent += _send_safely(chat_id, text, switch, audio_url=url, lang=chat_lang)
    return sent


def send_alert(case: dict, chat_ids: list[int] | None = None) -> int:
    """Village alert for one case. Used by the workflow when a case opens."""
    targets = chat_ids if chat_ids is not None else [s["chat_id"] for s in _relays(case)]
    return send_alert_group([case], targets)


def send_village_alerts(village_key: str, chat_id: int, lang: str | None = None) -> int:
    """Everything open in a village for one person: one alert per group of cases with the same advice."""
    from . import views

    bundle = views.village_bundle(village_key) or {"cases": []}
    open_cases = [store.get_case(c["case_id"]) for c in bundle["cases"] if c["status"] in store.OPEN_STATUSES]
    open_cases = [c for c in open_cases if c]
    sent = sum(send_alert_group(group, [chat_id], lang) for group in group_by_advice(open_cases))
    for case in open_cases:
        catch_up_relay(chat_id, case)
    return sent


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


def fix_buttons(case_id: str, short: str, lang: str = "hi") -> list:
    buttons = [[(i18n.t(f"fix_{action}", lang), f"f:{short}:{action}") for action in row] for row in FIX_ACTION_ROWS]
    buttons.append([(i18n.t("close_case", lang), f"x:{case_id}")])
    return buttons


def kit_message(case: dict, short: str, lang: str = "hi") -> tuple[str, list]:
    return (i18n.t("kit_request", lang, village=case["village"]),
            [[(i18n.t("kit_black", lang), f"k:{short}:contaminated"), (i18n.t("kit_yellow", lang), f"k:{short}:clean")]])


def _short(case_id: str, kind: str) -> str | None:
    tok = store.token_for_case(case_id, kind)
    return tok["pk"].split("#", 1)[1] if tok else None


def _engineer_card(chat_id: int, case: dict, short: str | None) -> bool:
    lang = store.chat_lang(chat_id)
    return _send_safely(chat_id, advice.engineer_card(case, lang), fix_buttons(case["case_id"], short, lang) if short else None)


CATCH_UP_LIMIT = 10


def catch_up_engineer(chat_id: int, block_key: str) -> int:
    """An engineer who joins after cases opened gets a card for each open case in the block, worst first."""
    open_cases = [c for c in store.block_cases(block_key) if c.get("status") in store.OPEN_STATUSES]
    open_cases.sort(key=lambda c: (rules.SEVERITY_ORDER.get(c.get("severity"), 9), c.get("opened_at", "")))
    sent = 0
    for c in open_cases[:CATCH_UP_LIMIT]:
        short = _short(c["case_id"], "fix") if c.get("status") in ("AWAITING_FIX", "ESCALATED") else None
        sent += _engineer_card(chat_id, c, short)
    if len(open_cases) > CATCH_UP_LIMIT:
        _tell(chat_id, "more_cases", n=len(open_cases) - CATCH_UP_LIMIT)
    return sent


def catch_up_relay(chat_id: int, case: dict) -> None:
    """A relay who joins while the village is waiting for a field-kit re-test gets the kit request too."""
    if case.get("status") == "AWAITING_RETEST" and (short := _short(case["case_id"], "kit")):
        text, buttons = kit_message(case, short, store.chat_lang(chat_id))
        _send_safely(chat_id, text, buttons)


def step_await_fix(case: dict, event: dict) -> None:
    short = _new_token(case["case_id"], "fix", event["token"])
    engineers = _engineers(case)
    for e in engineers:
        _engineer_card(e["chat_id"], case, short)
    store.update_case(case["case_id"], status="AWAITING_FIX")
    store.add_event(case["case_id"], "awaiting_fix",
                    note=f"asked {len(engineers)} engineer(s)" if engineers else "no engineer subscribed yet; waiting")


ESCALATION = {
    "fix": ("fix deadline passed", "escalation_fix", "AWAITING_FIX"),
    "retest": ("field-kit re-test overdue", "escalation_retest", "AWAITING_RETEST"),
    "lab": ("lab re-test overdue", "escalation_lab", "PROVISIONALLY_SAFE"),
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
        _tell(t["chat_id"], message, village=case["village"])
    return {"escalations": n}


def step_await_kit(case: dict, event: dict) -> None:
    short = _new_token(case["case_id"], "kit", event["token"])
    for r in _relays(case):
        text, buttons = kit_message(case, short, store.chat_lang(r["chat_id"]))
        _send_safely(r["chat_id"], text, buttons)
    store.update_case(case["case_id"], status="AWAITING_RETEST")
    store.add_event(case["case_id"], "awaiting_retest", note="field-kit re-test requested")


def step_reopen(case: dict, event: dict) -> None:
    store.update_case(case["case_id"], status="AWAITING_FIX")
    store.add_event(case["case_id"], "reopened", note=event.get("reason", "re-test not clean"))
    for r in _relays(case):
        _tell(r["chat_id"], "reopened", village=case["village"])


def step_provisional(case: dict, event: dict) -> dict:
    d = policy.decide("relay", "mark_provisional", case["case_id"], {"evidence": "kit_clean"})
    store.add_event(case["case_id"], "policy", decision="allow" if d["allowed"] else "deny", action="mark_provisional",
                    policies=d["policies"], reason=d["reason"])
    if d["allowed"]:
        store.update_case(case["case_id"], status="PROVISIONALLY_SAFE")
        for r in _relays(case):
            _tell(r["chat_id"], "provisional", village=case["village"])
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
        _tell(r["chat_id"], "closed", village=case["village"])
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
