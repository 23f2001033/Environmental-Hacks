"""Webhook and API routing with AWS and Telegram replaced by fakes."""

import json

import pytest

from jalsaathi import api, config, telegram, webhook


@pytest.fixture(autouse=True)
def fake_secrets(monkeypatch):
    secrets = {config.SSM_WEBHOOK_SECRET: "hook-secret", config.SSM_CONSOLE_TOKEN: "admin-token", config.SSM_BOT_TOKEN: "x"}
    monkeypatch.setattr(config, "secret", lambda name: secrets[name])


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(telegram, "send_message", lambda chat, text, buttons=None: out.append((chat, text, buttons)))
    monkeypatch.setattr(telegram, "answer_callback", lambda *a, **k: out.append(("answer", a, k)))
    monkeypatch.setattr(telegram, "clear_buttons", lambda *a, **k: None)
    return out


def _tg_event(update, secret="hook-secret"):
    return {"headers": {"X-Telegram-Bot-Api-Secret-Token": secret}, "body": json.dumps(update)}


def test_parse_update_kinds():
    assert telegram.parse_update({"update_id": 1, "message": {"chat": {"id": 5}, "text": "/start v_412558"}}) == {
        "update_id": 1, "kind": "command", "chat_id": 5, "name": None, "message_id": None, "command": "/start", "arg": "v_412558"}
    cb = telegram.parse_update({"update_id": 2, "callback_query": {"id": "c", "data": "s:v:1:y", "message": {"chat": {"id": 5}, "message_id": 9}}})
    assert cb["kind"] == "callback" and cb["data"] == "s:v:1:y" and cb["message_id"] == 9
    photo = telegram.parse_update({"update_id": 3, "message": {"chat": {"id": 5}, "photo": [{"file_id": "small"}, {"file_id": "big"}]}})
    assert photo["kind"] == "photo" and photo["file_id"] == "big"


def test_keyboard_uses_url_or_callback():
    kb = telegram.keyboard([[("Open", "https://example.org"), ("Yes", "s:v:1:y")]])
    assert kb["inline_keyboard"][0][0] == {"text": "Open", "url": "https://example.org"}
    assert kb["inline_keyboard"][0][1] == {"text": "Yes", "callback_data": "s:v:1:y"}


def test_webhook_rejects_wrong_secret():
    assert webhook.handler(_tg_event({"update_id": 1}, secret="nope"))["statusCode"] == 401


def test_webhook_ignores_duplicates(monkeypatch, sent):
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: True)
    resp = webhook.handler(_tg_event({"update_id": 7, "message": {"chat": {"id": 5}, "text": "/help"}}))
    assert resp == {"statusCode": 200, "body": "duplicate"} and sent == []


def test_webhook_start_with_village_asks_for_consent(monkeypatch, sent):
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: False)
    monkeypatch.setattr(webhook.store, "get_village", lambda key: {"key": key, "name": "BEHTA LAKHI"})
    webhook.handler(_tg_event({"update_id": 8, "message": {"chat": {"id": 5}, "text": "/start v_412558"}}))
    chat, text, buttons = sent[0]
    assert chat == 5 and "BEHTA LAKHI" in text
    assert buttons == [[("✅ हाँ", "s:v:412558:y"), ("❌ नहीं", "s:v:412558:n")]]


def test_webhook_close_attempt_is_denied_by_cedar(monkeypatch, sent):
    monkeypatch.setattr(webhook.store, "seen_update", lambda uid: False)
    events = []
    monkeypatch.setattr(webhook.actions.store, "add_event", lambda *a, **k: events.append((a, k)))
    webhook.handler(_tg_event({"update_id": 9, "callback_query": {"id": "c1", "data": "x:c-31-412558-ecoli",
                                                                  "message": {"chat": {"id": 5}, "message_id": 3}}}))
    assert events and events[0][1]["decision"] == "deny"
    answer = [s for s in sent if s[0] == "answer"][0]
    assert answer[2]["alert"] is True


def _api(path, method="GET", body=None, token=None):
    headers = {"x-admin-token": token} if token else {}
    return api.handler({"rawPath": path, "requestContext": {"http": {"method": method}}, "headers": headers,
                        "body": json.dumps(body or {})})


def test_api_health():
    resp = _api("/api/v1/health")
    assert resp["statusCode"] == 200 and json.loads(resp["body"])["ok"] is True


def test_api_admin_requires_token():
    assert _api("/api/v1/admin/reset", "POST")["statusCode"] == 401
    assert _api("/api/v1/admin/reset", "POST", token="wrong")["statusCode"] == 401


def test_api_unknown_route_and_method():
    assert _api("/api/v1/nope")["statusCode"] == 404
    assert _api("/api/v1/villages", "DELETE")["statusCode"] == 405


def test_api_village_not_found(monkeypatch):
    monkeypatch.setattr(api.views, "village_bundle", lambda key: None)
    assert _api("/api/v1/villages/zzz")["statusCode"] == 404
