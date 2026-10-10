"""Shared fakes: nobody has chosen a language unless a test says so (Hindi is the default)."""

import pytest

from jalsaathi import store


@pytest.fixture(autouse=True)
def default_language(monkeypatch):
    chosen = {}
    monkeypatch.setattr(store, "chat_lang", lambda chat_id: chosen.get(chat_id, "hi"))
    monkeypatch.setattr(store, "set_chat_lang", lambda chat_id, lang: chosen.__setitem__(chat_id, lang))
    return chosen
