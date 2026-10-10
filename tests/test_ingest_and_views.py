from jalsaathi import ingest, views, wqmis


def _planned():
    records, as_of = ingest.load("fixtures")
    return ingest.plan(records), as_of


def test_fixture_plan_makes_one_case_per_village_and_contaminant():
    planned, as_of = _planned()
    assert as_of == "2026-10-09"
    ids = [c["case_id"] for c in planned]
    assert len(ids) == len(set(ids)) == 13
    behta = next(c for c in planned if c["village"] == "BEHTA LAKHI")
    assert behta["case_id"] == "c-31-412558-ecoli" and behta["severity"] == "red" and behta["block_key"] == "5037"


def test_village_without_id_gets_a_slug_key_and_block_key():
    planned, _ = _planned()
    dhabla = next(c for c in planned if c["village"] == "Dhabla Kalayanpura")
    assert dhabla["village_key"] == "651384"
    assert dhabla["block_key"] == "4320"
    assert dhabla["code"] == "nitrate" and dhabla["severity"] == "red"


def test_plan_filters_by_village_name_or_key():
    records, _ = ingest.load("fixtures")
    assert [c["village"] for c in ingest.plan(records, ["behta lakhi"])] == ["BEHTA LAKHI"]
    assert [c["village"] for c in ingest.plan(records, ["412557"])] == ["Murcha"]


def test_plan_keeps_all_samples_and_the_worst_one():
    base = {"state_id": 31, "district": "D", "block": "B", "block_id": 1, "village": "V", "village_id": 9,
            "parameter": "Nitrate", "unit": "mg/l", "acceptable_limit": 45, "permissible_limit": 45}
    planned = ingest.plan([dict(base, value=50.0), dict(base, value=70.0), dict(base, value=40.0)])
    assert len(planned) == 1
    assert planned[0]["value"] == 70.0 and len(planned[0]["samples"]) == 2  # the 40 mg/l sample is within limits


def test_village_status_rules():
    assert views.village_status([]) == "unknown"
    assert views.village_status([{"status": "AWAITING_FIX"}]) == "unsafe"
    assert views.village_status([{"status": "PROVISIONALLY_SAFE"}]) == "provisional"
    assert views.village_status([{"status": "CLOSED"}]) == "safe_again"
    assert views.village_status([{"status": "CLOSED"}, {"status": "WARNED"}]) == "unsafe"


def test_wqmis_encryption_matches_the_portal():
    # Same key and IV as the portal's frmValidate.js; '0' encrypts to a fixed value.
    assert wqmis.enc(0) == wqmis.enc("0")
    assert len(wqmis.enc("2026-2027")) % 4 == 0


def test_wqmis_guard_flags_collapsed_counts():
    prev = {"UP:Ecoil": 19, "RJ:Nitrate": 50, "RJ:Fluoride": 0}
    assert wqmis.guard(prev, {"UP:Ecoil": 3, "RJ:Nitrate": 49}) == ["UP:Ecoil"]
    assert wqmis.guard(prev, {"UP:Ecoil": 0, "RJ:Nitrate": 50}) == ["UP:Ecoil"]
    assert wqmis.guard(prev, {"UP:Ecoil": 19, "RJ:Nitrate": 51}) == []
