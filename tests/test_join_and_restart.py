"""Engineers and relays who join late get what is waiting for them; restarting only the demo cases."""

import pytest

from jalsaathi import case_steps, ingest, webhook


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(case_steps, "_send_safely", lambda chat, text, buttons=None, audio_url=None: out.append((chat, text, buttons)) or True)
    return out


def _case(i, status="AWAITING_FIX", severity="red"):
    return {"case_id": f"c{i}", "status": status, "severity": severity, "opened_at": f"2026-10-10T0{i % 10}:00",
            "village": f"V{i}", "block": "Harpalpur", "district": "Hardoi", "code": "ecoli", "value": 80,
            "unit": "CFU/100 ml", "acceptable_limit": 0, "village_key": f"v{i}"}


def test_late_engineer_gets_cards_with_live_buttons_worst_first(monkeypatch, sent):
    cases = [_case(1, severity="amber"), _case(2), _case(3, status="AWAITING_RETEST"), _case(4, status="CLOSED")]
    monkeypatch.setattr(case_steps.store, "block_cases", lambda key: cases)
    monkeypatch.setattr(case_steps.store, "token_for_case",
                        lambda cid, kind: {"pk": f"TOK#s{cid}"} if kind == "fix" else None)
    assert case_steps.catch_up_engineer(9, "5037") == 3
    assert "V2" in sent[0][1]  # red, oldest first; amber last
    assert ["V3" in sent[1][1], "V1" in sent[2][1]] == [True, True]
    assert sent[0][2][0][0][1] == "f:sc2:chlorination" and sent[0][2][-1][0][1] == "x:c2"
    assert sent[1][2] is None  # waiting for the re-test, so no fix buttons
    assert sent[2][2][0][0][1] == "f:sc1:chlorination"


def test_late_engineer_in_a_busy_block_gets_a_count_not_a_flood(monkeypatch, sent):
    monkeypatch.setattr(case_steps.store, "block_cases", lambda key: [_case(i) for i in range(14)])
    monkeypatch.setattr(case_steps.store, "token_for_case", lambda cid, kind: None)
    assert case_steps.catch_up_engineer(9, "5037") == case_steps.CATCH_UP_LIMIT
    assert len(sent) == case_steps.CATCH_UP_LIMIT + 1 and "4 और" in sent[-1][1]


def test_late_relay_gets_the_waiting_kit_request(monkeypatch, sent):
    monkeypatch.setattr(case_steps.store, "token_for_case", lambda cid, kind: {"pk": "TOK#k1"} if kind == "kit" else None)
    case_steps.catch_up_relay(5, _case(1, status="AWAITING_RETEST"))
    case_steps.catch_up_relay(5, _case(2, status="AWAITING_FIX"))
    assert len(sent) == 1 and sent[0][2] == [[("⚫ काली (दूषित)", "k:k1:contaminated"), ("🟡 पीली (साफ़)", "k:k1:clean")]]


def test_engineer_consent_triggers_catch_up(monkeypatch):
    msgs, caught = [], []
    monkeypatch.setattr(webhook.config, "secret", lambda name: "hook-secret")
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: False)
    monkeypatch.setattr(webhook.store, "subscribe", lambda *a: None)
    monkeypatch.setattr(webhook.telegram, "send_message", lambda chat, text, buttons=None: msgs.append(text))
    monkeypatch.setattr(webhook.telegram, "answer_callback", lambda *a, **k: None)
    monkeypatch.setattr(webhook.telegram, "clear_buttons", lambda *a, **k: None)
    monkeypatch.setattr(webhook.case_steps, "catch_up_engineer", lambda chat, key: caught.append((chat, key)) or 0)
    monkeypatch.setattr(webhook.store, "block_cases", lambda key: [{"block": "Harpalpur"}])
    import json
    webhook.handler({"headers": {"X-Telegram-Bot-Api-Secret-Token": "hook-secret"}, "body": json.dumps(
        {"update_id": 30, "callback_query": {"id": "c", "data": "s:e:5037:y", "message": {"chat": {"id": 7}, "message_id": 1}}})})
    assert caught == [(7, "5037")] and "Harpalpur ब्लॉक" in msgs[0] and "कोई खुला मामला नहीं" in msgs[-1]


class FakeSfn:
    def __init__(self, names):
        self.names, self.stopped = names, []

    def get_paginator(self, op):
        names = self.names
        return type("P", (), {"paginate": lambda self, **k: [{"executions": [{"name": n, "executionArn": f"arn:{n}"} for n in names]}]})()

    def stop_execution(self, executionArn, cause):
        self.stopped.append(executionArn)


def test_restart_demo_touches_only_demo_cases(monkeypatch):
    records, _ = ingest.load("fixtures")
    demo_ids = {c["case_id"] for c in ingest.plan(records)}
    behta = "c-31-412558-ecoli"
    assert behta in demo_ids
    fake = FakeSfn([f"{behta}-a1b2c3", "c-27-999999-nitrate-1234abcd-20261010T001500", f"{behta}x-zzz"])
    monkeypatch.setattr(ingest.config, "client", lambda n: fake)
    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:CaseMachine")
    deleted, reseeded = [], []
    monkeypatch.setattr(ingest.store, "get_case", lambda cid: {"case_id": cid})
    monkeypatch.setattr(ingest.store, "delete_case", lambda cid, vkey: deleted.append(cid) or 3)
    monkeypatch.setattr(ingest, "handler", lambda event: reseeded.append(event) or {"new_cases": 13})
    result = ingest.restart_demo()
    assert fake.stopped == [f"arn:{behta}-a1b2c3"]  # the real case and a look-alike name are left alone
    assert set(deleted) == demo_ids and reseeded == [{"source": "fixtures"}]
    assert result["cases_removed"] == len(demo_ids) and result["cases_started"] == 13


def test_same_advice_cases_share_one_alert_but_boil_and_never_boil_never_do():
    ecoli = _case(1)
    coliform = dict(_case(2), code="coliform", value=200)
    nitrate = dict(_case(3), code="nitrate", value=60, unit="mg/l")
    groups = case_steps.group_by_advice([ecoli, nitrate, coliform])
    assert sorted(len(g) for g in groups) == [1, 2]
    assert {c["code"] for g in groups if len(g) == 2 for c in g} == {"ecoli", "coliform"}


def test_english_button_switches_language_and_resends_in_english(monkeypatch, default_language):
    import json
    answered, resent = [], []
    monkeypatch.setattr(webhook.config, "secret", lambda name: "hook-secret")
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: False)
    monkeypatch.setattr(webhook.telegram, "answer_callback", lambda cb, text=None, alert=False: answered.append(text))
    monkeypatch.setattr(webhook.case_steps, "send_village_alerts", lambda key, chat, lang=None: resent.append((key, chat, lang)))
    webhook.handler({"headers": {"X-Telegram-Bot-Api-Secret-Token": "hook-secret"}, "body": json.dumps(
        {"update_id": 31, "callback_query": {"id": "c", "data": "l:en:412558", "message": {"chat": {"id": 7}, "message_id": 1}}})})
    assert default_language[7] == "en" and resent == [("412558", 7, "en")] and "English" in answered[0]


def test_english_command_sets_language(monkeypatch, default_language):
    import json
    msgs = []
    monkeypatch.setattr(webhook.config, "secret", lambda name: "hook-secret")
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: False)
    monkeypatch.setattr(webhook.telegram, "send_message", lambda chat, text, buttons=None: msgs.append(text))
    webhook.handler({"headers": {"X-Telegram-Bot-Api-Secret-Token": "hook-secret"},
                     "body": json.dumps({"update_id": 32, "message": {"chat": {"id": 8}, "text": "/english"}})})
    assert default_language[8] == "en" and "English" in msgs[0]


def test_every_message_exists_in_both_languages():
    from jalsaathi import i18n
    for key, texts in i18n.MESSAGES.items():
        assert set(texts) == {"hi", "en"}, key
