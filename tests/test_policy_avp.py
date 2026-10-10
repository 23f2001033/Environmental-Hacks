"""Cedar decisions through Amazon Verified Permissions, with the local engine as a fail-safe fallback."""

import pytest

from jalsaathi import config, policy


def test_case_cedar_splits_into_four_named_policies():
    ids = [pid for pid, _ in policy.statements()]
    assert ids == ["close-needs-lab-pass", "kit-only-provisional", "messages-allowed", "no-boil-for-chemicals"]
    assert all(s.startswith(("permit", "forbid")) and s.endswith(";") for _, s in policy.statements())


def test_context_becomes_avp_attribute_values():
    assert policy._avp_value("chemical") == {"string": "chemical"}
    assert policy._avp_value(["boil"]) == {"set": [{"string": "boil"}]}
    assert policy._avp_value(True) == {"boolean": True} and policy._avp_value(3) == {"long": 3}


class FakeAVP:
    def __init__(self, response=None, fail=False):
        self.response, self.fail, self.calls = response, fail, []

    def is_authorized(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("AccessDenied")
        return self.response

    def list_policies(self, **kw):
        return {"policies": [{"policyId": "p1", "definition": {"static": {"description": "no-boil-for-chemicals"}}},
                             {"policyId": "p2", "definition": {"static": {"description": "close-needs-lab-pass"}}}]}


@pytest.fixture
def avp(monkeypatch):
    monkeypatch.setenv("AVP_POLICY_STORE_ID", "store-1")
    policy._avp_names.cache_clear()

    def install(fake):
        monkeypatch.setattr(config, "client", lambda name: fake)
        return fake
    return install


def test_verified_permissions_denial_names_our_policy(avp):
    fake = avp(FakeAVP({"decision": "DENY", "determiningPolicies": [{"policyId": "p1"}], "errors": []}))
    d = policy.decide("system", "send_message", "c1", {"contaminant_class": "chemical", "actions": ["boil"]})
    assert d == {"allowed": False, "action": "send_message", "policies": ["no-boil-for-chemicals"],
                 "engine": "verified-permissions", "reason": "forbidden by no-boil-for-chemicals"}
    call = fake.calls[0]
    assert call["principal"] == {"entityType": "Role", "entityId": "system"}
    assert call["context"]["contextMap"]["actions"] == {"set": [{"string": "boil"}]}


def test_evaluation_errors_deny_even_if_avp_allows(avp):
    avp(FakeAVP({"decision": "ALLOW", "determiningPolicies": [], "errors": [{"errorDescription": "missing attribute"}]}))
    d = policy.decide("system", "send_message", "c1", {})
    assert d["allowed"] is False and "fail closed" in d["reason"]


def test_service_failure_falls_back_to_the_same_policies_locally(avp):
    avp(FakeAVP(fail=True))
    d = policy.decide("engineer", "close_case", "c1", {"evidence": "engineer_says_fixed"})
    assert d["allowed"] is False and d["engine"] == "local-fallback"
    d = policy.decide("system", "close_case", "c1", {"evidence": "lab_pass"})
    assert d["allowed"] is True and d["policies"] == ["close-needs-lab-pass"]
