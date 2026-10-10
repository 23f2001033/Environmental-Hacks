import pytest

from jalsaathi import advice, policy, rules

CHEMICALS = ["nitrate", "fluoride", "arsenic"]
ALL = list(advice.library()["parameters"].keys())


@pytest.mark.parametrize("code", ALL)
def test_every_parameter_has_hindi_and_english_and_sources(code):
    e = advice.entry(code)
    assert e["name"]["hi"] and e["name"]["en"]
    assert e["do_now"], code
    for line in e["do_now"]:
        assert line["hi"].strip() and line["en"].strip() and line["action"]
    assert e["engineer_fix"]["hi"] and e["engineer_fix"]["en"]
    assert e["sources"]


@pytest.mark.parametrize("code", CHEMICALS)
def test_chemicals_never_advise_boiling(code):
    acts = advice.actions(code)
    assert "boil" not in acts and "chlorine" not in acts
    assert "no_boil" in acts and "alt_source" in acts


def test_nitrate_warns_about_infants():
    assert "infant_warning" in advice.actions("nitrate")


@pytest.mark.parametrize("code", ["ecoli", "coliform"])
def test_bacteria_advise_boiling_and_warn_clear_water(code):
    assert {"boil", "ors", "looks_clear_warning"} <= set(advice.actions(code))


@pytest.mark.parametrize("code", ALL)
def test_library_messages_pass_the_policy(code):
    d = policy.decide("system", "send_message", "c-test", advice.policy_context(code))
    assert d["allowed"], (code, d)


@pytest.mark.parametrize("code", CHEMICALS)
def test_policy_blocks_boil_advice_for_chemicals(code):
    ctx = {"contaminant_class": rules.contaminant_class(code), "actions": ["boil", "alt_source"]}
    d = policy.decide("system", "send_message", "c-test", ctx)
    assert not d["allowed"] and "no-boil-for-chemicals" in d["policies"]


def test_policy_fails_closed_on_missing_context():
    d = policy.decide("system", "send_message", "c-test", {})
    assert not d["allowed"] and "fail closed" in d["reason"]


@pytest.mark.parametrize("role,evidence,allowed", [
    ("engineer", "engineer_says_fixed", False),
    ("relay", "kit_clean", False),
    ("system", "lab_pass", True),
    ("engineer", "lab_pass", True),
])
def test_only_a_lab_pass_closes_a_case(role, evidence, allowed):
    d = policy.decide(role, "close_case", "c-test", {"evidence": evidence})
    assert d["allowed"] is allowed
    if allowed:
        assert d["policies"] == ["close-needs-lab-pass"]


def test_kit_clean_only_makes_a_case_provisional():
    assert policy.decide("relay", "mark_provisional", "c-test", {"evidence": "kit_clean"})["allowed"]
    assert not policy.decide("relay", "mark_provisional", "c-test", {"evidence": "looks_fine"})["allowed"]


def test_unknown_actions_are_denied():
    assert not policy.decide("engineer", "delete_case", "c-test", {"evidence": "lab_pass"})["allowed"]


CASE = {"code": "nitrate", "village": "Dhabla Kalayanpura", "block": "Anta", "district": "Baran", "value": 60.0,
        "unit": "mg/l", "acceptable_limit": 45.0, "lab_approval": "2026-08-05T12:55:00+05:30", "severity": "red"}


def test_alert_text_hindi_contains_facts_and_no_boil_warning():
    text = advice.alert_text(CASE, "hi", page_url="https://example.org/v/1", data_as_of="2026-10-09")
    assert "Dhabla Kalayanpura" in text and "60 mg/l" in text and "45" in text and "05-08-2026" in text
    assert "उबालें नहीं" in text and "https://example.org/v/1" in text


def test_alert_text_escapes_html():
    case = dict(CASE, village="<b>X</b>")
    assert "<b>X</b>" not in advice.alert_text(case, "en").replace("<b>&lt;b&gt;X&lt;/b&gt;", "")


def test_voice_script_is_plain_hindi():
    script = advice.voice_script(dict(CASE, code="ecoli", village="Behta Lakhi"))
    assert "Behta Lakhi" in script and "उबाल" in script and "<" not in script
