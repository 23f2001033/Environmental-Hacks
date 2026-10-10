"""Ask JalSaathi: the answer pipeline and every check that can replace the model's words with the official advice."""

import json

import pytest

from jalsaathi import assistant, store, telegram, webhook

NITRATE = {"case_id": "c-27-651384-nitrate", "code": "nitrate", "class": "chemical", "status": "AWAITING_FIX",
           "parameter_name": {"en": "nitrate", "hi": "नाइट्रेट"}, "value": 60, "unit": "mg/l", "acceptable_limit": 45,
           "lab_approval": "2026-08-05T12:55:00+05:30",
           "advice": {"en": ["Do not boil this water; boiling makes nitrate stronger.", "Use another tested source."],
                      "hi": ["इस पानी को उबालें नहीं।", "दूसरा जांचा हुआ स्रोत इस्तेमाल करें।"]},
           "timeline": [{"kind": "detected"}, {"kind": "warned"}]}
BUNDLE = {"village": {"key": "651384", "name": "Dhabla Kalayanpura", "block": "Anta", "district": "Baran", "state": "Rajasthan"},
          "status_text": {"en": "Unsafe water", "hi": "पानी असुरक्षित"}, "cases": [NITRATE]}


@pytest.fixture
def pipeline(monkeypatch):
    calls = {"recorded": []}
    monkeypatch.setattr(assistant.views, "village_bundle", lambda key: BUNDLE if key == "651384" else None)
    monkeypatch.setattr(assistant, "translate", lambda text, src, dst: f"[{dst}] {text}" if src != dst else text)
    monkeypatch.setattr(assistant, "run_agent", lambda q, facts: (calls.get("answer", "Do not boil this water."), [facts]))
    monkeypatch.setattr(assistant, "guardrail_check",
                        lambda q, g, a: calls.get("guard", {"passed": True, "grounding": 1.0, "relevance": 0.9, "blocked_topics": []}))
    monkeypatch.setattr(store, "add_event", lambda *a, **k: calls["recorded"].append(k))
    return calls


def test_facts_come_from_our_records(monkeypatch):
    monkeypatch.setattr(assistant.views, "village_bundle", lambda key: BUNDLE)
    facts, cases = assistant.village_facts("651384")
    assert "Dhabla Kalayanpura (Anta block" in facts and "nitrate measured 60 mg/l against a safe limit of 45" in facts
    assert "Do not boil this water" in facts and "No fix is recorded yet" in facts and cases == [NITRATE]


def test_grounded_answer_is_translated_back(pipeline):
    out = assistant.answer("651384", "क्या मैं उबालकर पी सकता हूं?", "hi")
    assert out["fallback"] is False and out["answer"] == "[hi] Do not boil this water."
    assert out["question_en"].startswith("[en]") and out["cedar"]["allowed"] is True
    assert pipeline["recorded"][0]["result"] == "grounded"


def test_ungrounded_answer_is_replaced_by_official_advice(pipeline):
    pipeline["guard"] = {"passed": False, "grounding": 0.1, "relevance": 0.9, "blocked_topics": ["false-all-clear"]}
    out = assistant.answer("651384", "is it fixed?", "en")
    assert out["fallback"] is True and "Do not boil this water" in out["answer"] and "ASHA" in out["answer"]
    assert pipeline["recorded"][0]["result"] == "fallback"


def test_cedar_blocks_boil_advice_for_chemical_contamination(pipeline):
    pipeline["answer"] = "Boil the water for one minute and it is safe."
    out = assistant.answer("651384", "what should I do?", "en")
    assert out["cedar"]["allowed"] is False and out["fallback"] is True
    assert "no-boil-for-chemicals" in out["cedar"]["policies"]


def test_model_failure_still_answers(monkeypatch, pipeline):
    monkeypatch.setattr(assistant, "run_agent", lambda q, f: (_ for _ in ()).throw(RuntimeError("throttled")))
    out = assistant.answer("651384", "help", "hi")
    assert out["fallback"] is True and "इस पानी को उबालें नहीं" in out["answer"]


def test_unknown_village_gets_a_plain_reply(pipeline):
    out = assistant.answer("999999", "is my water safe?", "en")
    assert out["fallback"] is True and "couldn't find" in out["answer"] and pipeline["recorded"] == []


@pytest.mark.parametrize("text,expected", [
    ("Boil the water for one minute.", True),
    ("Bring it to a rolling boil.", True),
    ("Do not boil this water; boiling makes nitrate stronger.", False),
    ("Never boil the water.", False),
    ("Boiling makes nitrate stronger.", False),
])
def test_advises_boiling(text, expected):
    assert assistant.advises_boiling(text) is expected


def test_contaminant_names_map_to_codes():
    assert [assistant.contaminant_code(n) for n in ("E. coli", "Total Coliform", "Nitrate")] == ["ecoli", "coliform", "nitrate"]
    assert "boiling does not remove it" in assistant.contaminant_text("fluoride")


def test_progress_reads_the_timeline():
    assert "logged a fix" in assistant._progress([{"kind": "fix_logged"}])
    assert "lab re-test passed" in assistant._progress([{"kind": "closed"}])


# --- Telegram routing ---------------------------------------------------------------------------------------------

def test_voice_note_is_parsed():
    u = telegram.parse_update({"update_id": 9, "message": {"chat": {"id": 5}, "voice": {"file_id": "v1", "duration": 4}}})
    assert u["kind"] == "voice" and u["file_id"] == "v1" and u["duration"] == 4


def _hook(update):
    return {"headers": {"X-Telegram-Bot-Api-Secret-Token": "hook-secret"}, "body": json.dumps(update)}


@pytest.fixture
def tg(monkeypatch):
    out = {"sent": [], "invoked": []}
    monkeypatch.setattr(webhook.config, "secret", lambda name: "hook-secret")
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: False)
    monkeypatch.setattr(webhook.telegram, "send_message", lambda chat, text, buttons=None: out["sent"].append(text))
    monkeypatch.setattr(webhook.config, "client", lambda n: type("L", (), {
        "invoke": lambda self, **k: out["invoked"].append(json.loads(k["Payload"]))})())
    return out


def test_voice_question_from_a_relay_is_answered_async(monkeypatch, tg):
    monkeypatch.setattr(webhook.store, "chat_subscriptions", lambda chat: [{"scope_pk": "VILLAGE#651384"}])
    webhook.handler(_hook({"update_id": 40, "message": {"chat": {"id": 5}, "voice": {"file_id": "v1", "duration": 5}}}))
    assert tg["invoked"] == [{"assistant": {"chat_id": 5, "village_key": "651384", "lang": "hi", "file_id": "v1"}}]
    assert "सवाल मिल गया" in tg["sent"][0]


def test_text_question_needs_a_village(monkeypatch, tg):
    monkeypatch.setattr(webhook.store, "chat_subscriptions", lambda chat: [])
    webhook.handler(_hook({"update_id": 41, "message": {"chat": {"id": 6}, "voice": {"file_id": "v2", "duration": 5}}}))
    assert tg["invoked"] == [] and "/start" in tg["sent"][0]


def test_long_voice_note_is_refused(monkeypatch, tg):
    monkeypatch.setattr(webhook.store, "chat_subscriptions", lambda chat: [{"scope_pk": "VILLAGE#651384"}])
    webhook.handler(_hook({"update_id": 42, "message": {"chat": {"id": 5}, "voice": {"file_id": "v3", "duration": 300}}}))
    assert tg["invoked"] == [] and "एक मिनट" in tg["sent"][0]


def test_async_job_runs_the_assistant(monkeypatch):
    ran = []
    monkeypatch.setattr(assistant, "handle_telegram", lambda job: ran.append(job) or {"ok": True})
    assert webhook.handler({"assistant": {"chat_id": 5, "village_key": "1", "text": "hi"}}) == {"ok": True} and ran
