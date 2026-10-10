"""District digest: one email per district official about overdue cases, never a flood."""

import json

import pytest

from jalsaathi import config, digest, ingest, store

CASES = [
    {"case_id": "c1", "village": "BEHTA LAKHI", "village_key": "412558", "block": "Harpalpur", "district": "Hardoi",
     "code": "ecoli", "value": 80, "unit": "CFU/ 100 ml", "lab_approval": "2026-06-15T10:00:00+05:30",
     "severity": "red", "status": "ESCALATED", "escalations": 2, "updated_at": "2026-10-10T10:00:00+00:00"},
    {"case_id": "c2", "village": "Murcha", "village_key": "412557", "block": "Harpalpur", "district": "Hardoi",
     "code": "coliform", "value": 30, "unit": "CFU/100 ml", "severity": "amber", "status": "AWAITING_FIX",
     "escalations": 1, "updated_at": "2026-10-10T09:00:00+00:00"},
    {"case_id": "c3", "village": "Dhabla Kalayanpura", "village_key": "651384", "block": "Anta", "district": "Baran",
     "code": "nitrate", "value": 60, "unit": "mg/l", "severity": "red", "status": "AWAITING_FIX", "escalations": 0},
    {"case_id": "c4", "village": "Basi", "village_key": "412542", "district": "Hardoi", "code": "ecoli",
     "status": "CLOSED", "escalations": 3},
]


def test_overdue_groups_open_escalated_cases_by_district():
    groups = digest.overdue(CASES)
    assert list(groups) == ["Hardoi"] and [c["case_id"] for c in groups["Hardoi"]] == ["c1", "c2"]


def test_email_names_villages_and_links_to_them(monkeypatch):
    monkeypatch.setenv("PUBLIC_DOMAIN", "example.org")
    subject, text, body = digest.render("Hardoi", digest.overdue(CASES)["Hardoi"])
    assert subject == "JalSaathi · Hardoi: 2 overdue drinking-water cases need action"
    assert "BEHTA LAKHI (Harpalpur): E. coli bacteria 80 CFU/100 ml" in text and "https://example.org/?v=412558" in text
    assert "<a href='https://example.org/?v=412558'>BEHTA LAKHI</a>" in body and "officials" in body


@pytest.fixture
def mail(monkeypatch):
    sent, state = [], {"last": None}
    secrets = {digest.SSM_RECIPIENTS: json.dumps({"Hardoi": ["dm@hardoi.example"], "*": ["team@example.org"]}),
               digest.SSM_SENDER: "alerts@example.org"}
    monkeypatch.setattr(config, "secret", lambda name: secrets[name])
    monkeypatch.setattr(config, "client", lambda name: type("SES", (), {"send_email": lambda self, **k: sent.append(k)})())
    monkeypatch.setattr(store, "list_cases", lambda: CASES)
    monkeypatch.setattr(store, "digest_sent_at", lambda d: state["last"])
    monkeypatch.setattr(store, "set_digest_sent", lambda d: state.update(last="2026-10-10T11:00:00+00:00"))
    monkeypatch.setattr(store, "add_event", lambda *a, **k: None)
    return sent


def test_one_email_per_district_then_quiet_until_something_changes(mail):
    assert digest.run() == {"sent": 1, "districts_overdue": 1}
    assert mail[0]["Destination"]["ToAddresses"] == ["dm@hardoi.example", "team@example.org"]
    assert mail[0]["FromEmailAddress"] == "alerts@example.org"
    assert digest.run()["sent"] == 0  # nothing updated since the last email
    assert digest.run(force=True)["sent"] == 1  # the admin console can send now


def test_not_configured_sends_nothing(monkeypatch):
    monkeypatch.setattr(config, "secret", lambda name: (_ for _ in ()).throw(RuntimeError("ParameterNotFound")))
    assert digest.run() == {"sent": 0, "skipped": "not configured"}


def test_scheduler_event_reaches_the_digest(monkeypatch):
    called = []
    monkeypatch.setattr(digest, "run", lambda force=False: called.append(force) or {"sent": 0})
    ingest.handler({"action": "district_digest"})
    ingest.handler({"action": "district_digest", "force": True})
    assert called == [False, True]
