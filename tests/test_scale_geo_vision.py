"""Scale run, geocoding validation, lazy audio, AI kit hint, stats and cost estimate. AWS replaced by fakes."""

import json
import re

import pytest

from jalsaathi import actions, api, case_steps, config, costs, geo, ingest, vision, voice

# --- geocoding -------------------------------------------------------------------------------------------------------

JAIPUR = {"Title": "Kalayanpura, Sanganer, Jaipur, Rajasthan, India", "PlaceType": "SubDistrict", "Position": [75.77, 26.83],
          "Address": {"SubRegion": {"Name": "Jaipur"}, "Region": {"Name": "Rajasthan"}}}
FLOUR_MILL = {"Title": "Bhangarh Flour Mill", "PlaceType": "PointOfInterest", "Position": [76.51, 25.09],
              "Address": {"SubRegion": {"Name": "Baran"}}}
BEHTA = {"Title": "Behta Lakhi, Sawayajpur, Uttar Pradesh, India", "PlaceType": "District", "Position": [79.779931, 27.237251],
         "Address": {"SubRegion": {"Name": "Hardoi"}}}
ANTA = {"Title": "Anta, Baran, Rajasthan, India", "PlaceType": "Locality", "Position": [76.30, 25.15],
        "Address": {"SubRegion": {"Name": "Baran"}}}


def test_geocode_rejects_wrong_district_and_shops():
    assert geo.pick([JAIPUR], "Dhabla Kalayanpura", "Baran") is None
    assert geo.pick([FLOUR_MILL], "Bhajangarh", "Baran") is None


def test_geocode_accepts_matching_village():
    assert geo.pick([JAIPUR, BEHTA], "BEHTA LAKHI", "Hardoi") == {"lat": 27.23725, "lon": 79.77993,
                                                                 "geo_title": BEHTA["Title"]}


BARAN_TOWN = {"Title": "Baran, Rajasthan, India", "PlaceType": "Locality", "Position": [76.50895, 25.09606],
              "Address": {"SubRegion": {"Name": "Baran"}}}


def test_geocode_falls_back_to_block_once_per_block(monkeypatch):
    monkeypatch.setattr(geo, "_geocode", lambda q: [ANTA] if q.startswith("Anta") else [JAIPUR])
    cache = {}
    first, n1 = geo.locate("Dhabla Kalayanpura", "Anta", "Baran", "Rajasthan", cache)
    second, n2 = geo.locate("Bhajangarh", "Anta", "Baran", "Rajasthan", cache)
    assert first["geo_precision"] == second["geo_precision"] == "block" and first["lat"] == 25.15
    assert (n1, n2) == (2, 1)


def test_block_query_answered_with_district_town_is_labelled_district(monkeypatch):
    # The real geocoder answers "Anta, Baran" with Baran town; that must not be called the block.
    monkeypatch.setattr(geo, "_geocode", lambda q: [BARAN_TOWN])
    found, calls = geo.locate("Dhabla Kalayanpura", "Anta", "Baran", "Rajasthan", {})
    assert found["geo_precision"] == "district" and calls == 3


def test_geocode_failure_never_raises(monkeypatch):
    monkeypatch.setattr(geo, "_geocode", lambda q: (_ for _ in ()).throw(RuntimeError("throttled")))
    assert geo.locate("V", "B", "D", "S", {})[0] == {}


# --- ingest: timers, names, villages ---------------------------------------------------------------------------------

def test_demo_clock_only_for_fixtures(monkeypatch):
    monkeypatch.setenv("DEMO_CLOCK", "1")
    assert ingest.use_demo_clock("fixtures", {}) is True
    assert ingest.use_demo_clock("snapshot", {}) is False
    assert ingest.use_demo_clock("live", {"demo_clock": True}) is True


def test_exec_names_are_deterministic_and_valid():
    a = ingest.exec_name("c-31-412558-ecoli", "20261010T101500-snapshot")
    assert a == ingest.exec_name("c-31-412558-ecoli", "20261010T101500-snapshot")
    assert a != ingest.exec_name("c-31-412558-ecoli", "20261010T111500-snapshot")
    long = ingest.exec_name("c-" + "x" * 78, "20261010T101500-snapshot")
    assert len(long) <= 80 and re.fullmatch(r"[A-Za-z0-9_-]+", long)


def test_village_item_keeps_coordinates_and_demo_flag():
    c = {"village_key": "9", "village": "V", "block_key": "1"}
    v = ingest.village_item(c, "2026-10-09", "snapshot", {"lat": 25.1, "lon": 76.3, "geo_precision": "block", "source": "fixtures"})
    assert (v["lat"], v["geo_precision"], v["source"]) == (25.1, "block", "fixtures")


class FakeStore:
    def __init__(self):
        self.villages, self.cases, self.runs = {}, {}, []

    def install(self, monkeypatch):
        s = ingest.store
        monkeypatch.setattr(s, "get_village", lambda k: self.villages.get(k))
        monkeypatch.setattr(s, "put_village", lambda v: self.villages.__setitem__(v["key"], v))
        monkeypatch.setattr(s, "put_sample", lambda k, smp: True)
        monkeypatch.setattr(s, "create_case", lambda c: c["case_id"] not in self.cases and not self.cases.__setitem__(c["case_id"], c))
        monkeypatch.setattr(s, "put_run", self.runs.append)


class FakeAws:
    def __init__(self):
        self.started, self.objects, self.scale = [], {}, []

    def start_execution(self, stateMachineArn, name, input):
        (self.scale if "Scale" in stateMachineArn else self.started).append((name, json.loads(input)))
        return {"executionArn": f"arn:{name}"}

    def list_executions(self, **kw):
        return {"executions": []}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = json.loads(Body)


@pytest.fixture
def aws(monkeypatch):
    fake = FakeAws()
    monkeypatch.setattr(config, "client", lambda name: fake)
    monkeypatch.setenv("STATE_MACHINE_ARN", "arn:CaseMachine")
    monkeypatch.setenv("SCALE_RUN_ARN", "arn:ScaleRun")
    monkeypatch.setenv("DEMO_CLOCK", "1")
    return fake


def test_small_fixture_run_starts_workflows_directly_with_demo_timers(monkeypatch, aws):
    fs = FakeStore()
    fs.install(monkeypatch)
    run = ingest.handler({"source": "fixtures", "geocode": False})
    assert run["new_cases"] == run["workflows_started"] == len(aws.started) == 13 and not aws.scale
    assert aws.started[0][1]["timers"]["fix_seconds"] < 3600 and run["demo_clock"] is True
    assert run["cost_estimate"]["usd_total"] > 0
    assert ingest.handler({"source": "fixtures", "geocode": False})["new_cases"] == 0  # idempotent


def test_scale_run_writes_items_and_uses_real_timers(monkeypatch, aws):
    fs = FakeStore()
    fs.install(monkeypatch)
    run = ingest.handler({"source": "fixtures", "geocode": False, "scale": True, "demo_clock": False})
    items = aws.objects[ingest.SCALE_ITEMS_KEY]
    assert run["scale_run"] is True and run["workflows_started"] == 0 and not aws.started
    assert len(items) == 13 and {"case_id", "timers", "exec_name"} == set(items[0])
    assert items[0]["timers"]["fix_seconds"] == 48 * 3600 or items[0]["timers"]["fix_seconds"] >= 7 * 86400
    assert aws.scale[0][1] == {"run_id": run["run_id"], "items": 13}


def test_reset_is_handled_by_ingest(monkeypatch, aws):
    monkeypatch.setattr(ingest, "_stop_all", lambda arn: 2)
    monkeypatch.setattr(ingest.store, "reset_demo", lambda: 40)
    assert ingest.handler({"action": "reset"})["workflows_stopped"] == 4


# --- lazy audio -----------------------------------------------------------------------------------------------------

def test_no_voice_note_when_nobody_is_listening(monkeypatch):
    made = []
    monkeypatch.setattr(voice, "synthesize", lambda text, key, lang="hi": made.append(key) or "/media/x")
    monkeypatch.setattr(case_steps, "_relays", lambda case: [])
    assert case_steps.send_alert({"case_id": "c1", "village_key": "9"}) == 0 and made == []


def test_voice_note_is_made_once(monkeypatch):
    made, updates = [], []
    monkeypatch.setattr(voice, "synthesize", lambda text, key, lang="hi": made.append(key) or f"/media/{key}")
    monkeypatch.setattr("jalsaathi.store.update_case", lambda cid, **f: updates.append(f))
    monkeypatch.setattr("jalsaathi.advice.voice_script", lambda case, lang="hi": "नमस्ते")
    case = {"case_id": "c1"}
    assert voice.ensure_audio(case) == voice.ensure_audio(case) == "/media/audio/c1.mp3"
    assert made == ["audio/c1.mp3"] and updates == [{"audio_path": "/media/audio/c1.mp3"}]


# --- AI kit hint ----------------------------------------------------------------------------------------------------

def test_parse_hint():
    assert vision.parse_hint('```json\n{"colour": "Black", "confidence": "high", "reason": "dark liquid"}\n```')["colour"] == "black"
    assert vision.parse_hint('{"colour": "purple"}') is None
    assert vision.parse_hint("no idea") is None
    assert vision.parse_hint('{"colour": "yellow", "confidence": "sure"}')["confidence"] == "low"


def test_hint_message_says_it_is_only_a_suggestion():
    assert "सुझाव" in vision.hint_message({"colour": "black", "confidence": "high"})
    assert "only a suggestion" in vision.hint_message({"colour": "yellow", "confidence": "low"}, "en")
    assert "AI" not in vision.hint_message(None)


def test_kit_result_records_whether_person_agreed_with_ai(monkeypatch):
    events = []
    monkeypatch.setattr(actions.store, "add_event", lambda *a, **k: events.append(k))
    monkeypatch.setattr(actions.store, "token_for_case", lambda case_id, kind: {"pk": "TOK#a", "token": "T"})
    monkeypatch.setattr(actions.store, "delete_token", lambda *a: None)
    monkeypatch.setattr(actions.config, "client", lambda n: type("S", (), {"send_task_success": lambda self, **k: None})())
    actions.kit_result("c1", "contaminated", "tg:1", None, {"colour": "yellow", "confidence": "medium"})
    assert "person chose differently" in events[0]["note"] and events[0]["ai_hint"]["colour"] == "yellow"


# --- stats, config, admin routes, cost ------------------------------------------------------------------------------

def test_alert_latency():
    cases = [{"opened_at": "2026-10-10T10:00:00+00:00", "warned_at": f"2026-10-10T10:00:{s:02d}+00:00"} for s in (2, 4, 30)]
    assert api.alert_latency(cases + [{"opened_at": "2026-10-10T10:00:00+00:00"}]) == {
        "cases": 3, "median_s": 4.0, "p95_s": 30.0, "max_s": 30.0}
    assert api.alert_latency([]) is None


def test_repeat_failures_are_bundled():
    totals = api.repeat_failures()["totals"]
    assert totals["both"] > 0 and totals["last_year"] >= totals["both"]


@pytest.fixture
def admin_ok(monkeypatch):
    monkeypatch.setattr(config, "secret", lambda name: "admin-token")


def _post(path, body=None):
    return api.handler({"rawPath": path, "requestContext": {"http": {"method": "POST"}},
                        "headers": {"x-admin-token": "admin-token"}, "body": json.dumps(body or {})})


def test_admin_scale_run_and_reset_run_async(monkeypatch, admin_ok):
    invoked = []
    monkeypatch.setattr(config, "client", lambda n: type("L", (), {"invoke": lambda self, **k: invoked.append(json.loads(k["Payload"]))})())
    assert _post("/api/v1/admin/scale-run")["statusCode"] == 202
    assert _post("/api/v1/admin/reset")["statusCode"] == 202
    assert _post("/api/v1/admin/restart-demo")["statusCode"] == 202
    assert _post("/api/v1/admin/ingest", {"source": "s3://evil"})["statusCode"] == 400
    assert invoked == [{"source": "snapshot", "scale": True}, {"action": "reset"}, {"action": "restart_demo"}]


def test_config_without_map_key(monkeypatch):
    monkeypatch.delenv("MAP_KEY_NAME", raising=False)
    api._map_key.cache_clear()
    resp = api.handler({"rawPath": "/api/v1/config", "requestContext": {"http": {"method": "GET"}}})
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200 and body["map"]["style_url"] is None and body["bot"]


def test_cost_estimate_has_assumptions():
    est = costs.estimate(580, 0, 900, 580)
    assert est["usd_total"] == pytest.approx(sum(est["usd_by_service"].values()), abs=1e-3)
    assert est["usd_total"] < 5 and "prices" in est["assumptions"]
    assert costs.estimate(0, 0, 0)["usd_per_case"] is None


def test_kit_hint_uses_nova_and_stops_asking_a_refused_model(monkeypatch):
    asked = []

    class Bedrock:
        def __init__(self, deny):
            self.deny = deny

        def converse(self, modelId, **kw):
            asked.append(modelId)
            if self.deny:
                raise RuntimeError("AccessDeniedException: model access")
            return {"output": {"message": {"content": [{"text": '{"colour": "black", "confidence": "high", "reason": "dark"}'}]}}}

    monkeypatch.setattr(vision, "_unavailable", set())
    monkeypatch.setattr(config, "client", lambda n: Bedrock(deny=False))
    assert vision.kit_hint(b"jpeg") == {"colour": "black", "confidence": "high", "reason": "dark", "model": vision.MODEL_ID}
    monkeypatch.setattr(config, "client", lambda n: Bedrock(deny=True))
    assert vision.kit_hint(b"jpeg") is None and vision.kit_hint(b"jpeg") is None
    assert asked == [vision.MODEL_ID, vision.MODEL_ID]  # refused once, then not asked again
