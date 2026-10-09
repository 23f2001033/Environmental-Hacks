import pytest

from jalsaathi import actions


@pytest.fixture
def recorded(monkeypatch):
    events = []
    monkeypatch.setattr(actions.store, "add_event", lambda *a, **k: events.append((a, k)))
    monkeypatch.setattr(actions.store, "token_for_case", lambda case_id, kind: None)
    return events


@pytest.mark.parametrize("call", [
    lambda: actions.lab_result("c1", "pass", "t", simulated=True),
    lambda: actions.kit_result("c1", "clean", "t", None),
    lambda: actions.log_fix("c1", "chlorination", "t"),
])
def test_rejected_actions_leave_no_trace(recorded, call):
    with pytest.raises(actions.ActionError):
        call()
    assert recorded == []


def test_unknown_values_are_rejected_before_anything(recorded):
    for call in (lambda: actions.lab_result("c1", "maybe", "t", True), lambda: actions.kit_result("c1", "grey", "t", None),
                 lambda: actions.log_fix("c1", "prayed", "t")):
        with pytest.raises(actions.ActionError):
            call()
    assert recorded == []


def test_accepted_action_records_then_resumes(monkeypatch, recorded):
    sent = []
    monkeypatch.setattr(actions.store, "token_for_case", lambda case_id, kind: {"pk": "TOK#abc", "token": "T"})
    monkeypatch.setattr(actions.store, "delete_token", lambda *a: sent.append(("deleted", a)))

    class FakeSfn:
        def send_task_success(self, taskToken, output):
            sent.append(("success", taskToken, output))

    monkeypatch.setattr(actions.config, "client", lambda name: FakeSfn())
    actions.kit_result("c1", "clean", "tg:1", "private/kit/c1/x.jpg")
    assert recorded[0][0] == ("c1", "kit_result") and recorded[0][1]["result"] == "clean"
    assert sent[0] == ("success", "T", '{"result": "clean"}') and sent[1] == ("deleted", ("abc", "c1", "kit"))
