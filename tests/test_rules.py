import pytest

from jalsaathi import rules


@pytest.mark.parametrize("name,code", [
    ("Ecoil", "ecoli"), ("TotalEcoil", "ecoli"), ("Coliform", "coliform"), ("Nitrate", "nitrate"),
    ("Fluoride", "fluoride"), ("Total arsenic", "arsenic"), ("TDS", "tds"), ("Iron", "iron"), ("Unknown", None),
])
def test_param_code(name, code):
    assert rules.param_code(name) == code


@pytest.mark.parametrize("code,value,acc,perm,expected", [
    ("ecoli", 80, 0, 0, "red"),
    ("ecoli", 0, 0, 0, "review"),
    ("coliform", 3, 0, 0, "red"),
    ("nitrate", 60, 45, 45, "red"),
    ("nitrate", 40, 45, 45, "review"),
    ("fluoride", 1.8, 1.0, 1.5, "amber"),
    ("fluoride", 1.2, 1.0, 1.5, "yellow"),
    ("arsenic", 0.08, 0.01, 0.05, "red"),
    ("arsenic", 0.03, 0.01, 0.05, "amber"),
    ("tds", 2500, 500, 2000, "amber"),
    ("tds", 900, 500, 2000, "yellow"),
    ("iron", 1.4, 1.0, 1.0, "yellow"),
    ("turbidity", 7, 1, 5, "amber"),
    ("chlorine", 0.1, 0.2, 1.0, "amber"),
    ("nitrate", None, 45, 45, "review"),
    ("mystery", 5, 1, 2, "review"),
])
def test_severity(code, value, acc, perm, expected):
    assert rules.severity(code, value, acc, perm) == expected


def test_severity_uses_default_limits_when_missing():
    assert rules.severity("nitrate", 60, None, None) == "red"
    assert rules.severity("fluoride", 1.6, None, None) == "amber"


def test_demo_timers_are_minutes_and_real_timers_are_days():
    demo, real = rules.timers("red", True), rules.timers("red", False)
    assert demo["fix_seconds"] <= 600 and real["fix_seconds"] == 48 * 3600
    assert real["retest_seconds"] == 7 * 86400


def test_case_id_is_stable_and_step_functions_safe():
    cid = rules.case_id(31, "412558", "ecoli")
    assert cid == "c-31-412558-ecoli"
    assert rules.case_id(31, "412558", "ecoli") == cid
    long = rules.case_id(27, "x" * 200, "nitrate")
    assert len(long) <= 80 and all(ch.isalnum() or ch in "-_" for ch in long)
