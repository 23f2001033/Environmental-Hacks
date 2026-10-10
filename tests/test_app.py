"""Web app: signed links, engineer and relay actions, Web Push encryption, officials' overview and activity feed."""

import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from jalsaathi import api, app_api, case_steps, config, links, notify, store, webpush


@pytest.fixture(autouse=True)
def secrets_(monkeypatch):
    monkeypatch.setattr(config, "secret", lambda name: {config.SSM_CONSOLE_TOKEN: "admin-token",
                                                        config.SSM_VAPID_PRIVATE: VAPID}.get(name, "x"))


VAPID = webpush.new_vapid_private()


def _call(method, path, body=None, query=None):
    resp = api.handler({"rawPath": path, "requestContext": {"http": {"method": method}}, "headers": {},
                        "body": json.dumps(body or {}), "queryStringParameters": query})
    return resp["statusCode"], json.loads(resp["body"])


# --- Web Push: decrypt what we encrypt, the way a browser does (RFC 8291) -----------------------------------------

def test_web_push_message_decrypts_like_a_browser():
    browser = ec.generate_private_key(ec.SECP256R1())
    auth = b"0123456789abcdef"
    body = webpush.encrypt(b'{"title":"JalSaathi"}', webpush.b64u(webpush.public_bytes(browser)), webpush.b64u(auth))
    salt, rs, idlen = body[:16], int.from_bytes(body[16:20], "big"), body[20]
    server_public = body[21:21 + idlen]
    shared = browser.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), server_public))
    ikm = webpush._hkdf(auth, shared, b"WebPush: info\x00" + webpush.public_bytes(browser) + server_public, 32)
    cek = webpush._hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = webpush._hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert rs == 4096 and plain == b'{"title":"JalSaathi"}\x02'


def test_vapid_header_is_a_valid_es256_jwt():
    header = webpush.vapid_header("https://fcm.googleapis.com/fcm/send/abc", VAPID, "https://example.org")
    jwt, k = header[len("vapid t="):].split(", k=")
    head, claims, sig = jwt.split(".")
    assert json.loads(webpush.unb64u(claims))["aud"] == "https://fcm.googleapis.com"
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), webpush.unb64u(k))
    raw = webpush.unb64u(sig)
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    public.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
                  f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))  # raises if invalid


def test_gone_subscriptions_are_removed(monkeypatch):
    removed = []
    monkeypatch.setattr(store, "push_subscribers", lambda scope: [{"sk": "PUSH#a", "lang": "en", "subscription": {}},
                                                                  {"sk": "PUSH#b", "lang": "hi", "subscription": {}}])
    monkeypatch.setattr(store, "push_unsubscribe", lambda scope, sk: removed.append(sk))
    statuses = iter([201, 410])
    sent = []
    monkeypatch.setattr(webpush, "send", lambda sub, msg: sent.append(msg) or next(statuses))
    case = {"case_id": "c1", "village": "Behta Lakhi", "village_key": "412558", "code": "ecoli"}
    assert notify.village(case, "push_alert") == 1 and removed == ["PUSH#b"]
    assert sent[0]["body"].startswith("Behta Lakhi: the water test found E. coli") and sent[0]["url"].endswith("/village/412558")
    assert "<" not in sent[1]["body"]


# --- signed links -------------------------------------------------------------------------------------------------

def test_links_are_specific_to_role_and_place():
    t = links.token("e", "5037")
    assert links.verify("e", "5037", t)
    assert not links.verify("e", "5038", t) and not links.verify("v", "5037", t) and not links.verify("e", "5037", None)
    assert _call("GET", "/api/v1/access", query={"role": "e", "key": "5037", "k": t}) == (200, {"valid": True})


# --- engineer and relay actions --------------------------------------------------------------------------------

CASE = {"case_id": "c-31-412558-ecoli", "block_key": "5037", "village_key": "412558", "code": "ecoli"}


@pytest.fixture
def recorded(monkeypatch):
    calls = []
    monkeypatch.setattr(store, "get_case", lambda cid: dict(CASE) if cid == CASE["case_id"] else None)
    monkeypatch.setattr(app_api.actions, "log_fix", lambda *a: calls.append(("fix",) + a))
    monkeypatch.setattr(app_api.actions, "try_close", lambda *a: calls.append(("close",) + a) or
                        {"allowed": False, "policies": [], "reason": "no policy permits this"})
    monkeypatch.setattr(app_api.actions, "kit_result", lambda *a: calls.append(("kit",) + a))
    monkeypatch.setattr(app_api.actions, "require_waiting", lambda cid, kind: {"token": "T"})
    return calls


def test_engineer_needs_the_block_link(recorded):
    status, _ = _call("POST", "/api/v1/engineer/5037/fix", {"case_id": CASE["case_id"], "action": "chlorination", "k": "wrong"})
    assert status == 401 and recorded == []
    k = links.token("e", "5037")
    assert _call("POST", "/api/v1/engineer/5038/fix", {"case_id": CASE["case_id"], "k": links.token("e", "5038")})[0] == 404
    assert _call("POST", "/api/v1/engineer/5037/fix", {"case_id": CASE["case_id"], "action": "chlorination", "k": k})[0] == 200
    status, body = _call("POST", "/api/v1/engineer/5037/close", {"case_id": CASE["case_id"], "k": k})
    assert status == 200 and body["allowed"] is False
    assert [c[0] for c in recorded] == ["fix", "close"] and recorded[0][3] == "web app (engineer)"


def test_relay_photo_hint_and_kit_result(monkeypatch, recorded):
    k = links.token("v", "412558")

    class S3:
        def get_object(self, Bucket, Key):
            return {"ContentLength": 10, "Body": type("B", (), {"read": lambda self: b"jpeg"})()}

    monkeypatch.setattr(app_api, "_s3_presigner", lambda: type("P", (), {
        "generate_presigned_url": lambda self, op, Params, ExpiresIn: f"https://s3/{Params['Key']}?sig"})())
    monkeypatch.setattr(config, "client", lambda n: S3())
    monkeypatch.setattr(app_api.vision, "kit_hint", lambda img: {"colour": "yellow", "confidence": "high"})
    hints = {}
    monkeypatch.setattr(store, "put_photo_hint", lambda key, hint: hints.__setitem__(key, hint))
    monkeypatch.setattr(store, "photo_hint", lambda key: hints.get(key))

    status, up = _call("POST", "/api/v1/relay/412558/upload", {"case_id": CASE["case_id"], "k": k})
    assert status == 200 and up["photo_key"].startswith(f"private/kit/{CASE['case_id']}/")
    assert _call("POST", "/api/v1/relay/412558/hint", {"case_id": CASE["case_id"], "k": k, "photo_key": "private/kit/other/x.jpg"})[0] == 400
    status, hint = _call("POST", "/api/v1/relay/412558/hint", {"case_id": CASE["case_id"], "k": k, "photo_key": up["photo_key"], "lang": "en"})
    assert status == 200 and hint["hint"]["colour"] == "yellow" and "yellow" in hint["message"]
    assert _call("POST", "/api/v1/relay/412558/kit", {"case_id": CASE["case_id"], "k": k, "result": "clean"})[0] == 400  # no photo
    assert _call("POST", "/api/v1/relay/412558/kit", {"case_id": CASE["case_id"], "k": k, "result": "clean",
                                                       "photo_key": up["photo_key"]})[0] == 200
    assert recorded[-1] == ("kit", CASE["case_id"], "clean", "web app (relay)", up["photo_key"], {"colour": "yellow", "confidence": "high"})


def test_push_subscribe_only_accepts_browser_push_services(monkeypatch):
    saved = []
    monkeypatch.setattr(store, "get_village", lambda key: {"key": key})
    monkeypatch.setattr(store, "push_subscribe", lambda scope, sub, lang: saved.append((scope, sub["endpoint"], lang)))
    sub = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "p", "auth": "a"}}
    assert _call("POST", "/api/v1/push/subscribe", {"scope": "village", "key": "412558", "subscription": sub, "lang": "en"})[0] == 200
    evil = dict(sub, endpoint="https://169.254.169.254/latest")
    assert _call("POST", "/api/v1/push/subscribe", {"scope": "village", "key": "412558", "subscription": evil})[0] == 400
    assert saved == [("VILLAGE#412558", sub["endpoint"], "en")]


# --- officials ----------------------------------------------------------------------------------------------------

def test_overview_counts_open_overdue_and_chemical_share(monkeypatch):
    cases = [
        {"state": "UP", "district": "Hardoi", "block_key": "5037", "block": "Harpalpur", "village_key": "1",
         "status": "ESCALATED", "escalations": 1, "severity": "red", "code": "ecoli"},
        {"state": "UP", "district": "Hardoi", "block_key": "5037", "block": "Harpalpur", "village_key": "2",
         "status": "AWAITING_FIX", "severity": "red", "code": "nitrate"},
        {"state": "UP", "district": "Hardoi", "block_key": "5038", "block": "Other", "village_key": "3",
         "status": "CLOSED", "severity": "red", "code": "ecoli"},
        {"state": "RJ", "district": "Baran", "block_key": "4320", "block": "Anta", "village_key": "4",
         "status": "AWAITING_FIX", "severity": "amber", "code": "fluoride"},
    ]
    monkeypatch.setattr(store, "list_cases", lambda: cases)
    status, body = _call("GET", "/api/v1/overview")
    hardoi = body["districts"][0]
    assert status == 200 and hardoi["district"] == "Hardoi" and hardoi["escalated"] == 1 and hardoi["open"] == 2
    assert hardoi["closed"] == 1 and hardoi["chemical_share"] == 0.5 and [b["block"] for b in hardoi["blocks"]] == ["Harpalpur"]
    assert body["totals"] == {"open": 3, "closed": 1, "provisional": 0, "escalated": 1, "villages": 3}


def test_activity_feed_joins_case_details(monkeypatch):
    monkeypatch.setattr(store, "feed", lambda limit: [
        {"case_id": CASE["case_id"], "kind": "policy", "decision": "deny", "action": "close_case", "at": "t1"},
        {"case_id": "gone", "kind": "detected", "at": "t0"}])
    monkeypatch.setattr(store, "get_case", lambda cid: dict(CASE, village="BEHTA LAKHI") if cid == CASE["case_id"] else None)
    status, body = _call("GET", "/api/v1/activity")
    assert status == 200 and len(body["events"]) == 1 and body["events"][0]["village"] == "BEHTA LAKHI"
    assert body["events"][0]["decision"] == "deny"


def test_deadline_is_set_while_waiting_and_cleared_after_last_escalation(monkeypatch):
    case = {"timers": {"fix_seconds": 240}}
    assert case_steps._deadline(case, {}, "fix_seconds") > store.now_iso()
    assert case_steps._deadline(case, {"no_deadline": True}, "fix_seconds") is None
