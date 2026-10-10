"""Signed web-app links for village relays and block engineers: no passwords, one link per village or block.

A link carries an HMAC of (role, key); the server checks it before any action. Cedar still decides what the role
may do (an engineer link can log a fix but can never close a case).
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from . import config

ROLES = {"v": "relay", "e": "engineer"}


def token(role: str, key: str) -> str:
    secret = config.secret(config.SSM_CONSOLE_TOKEN).encode()
    digest = hmac.new(secret, f"jalsaathi-link:{role}:{key}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()[:22]


def verify(role: str, key: str, supplied: str | None) -> bool:
    return bool(supplied) and hmac.compare_digest(token(role, key), supplied)


def url(role: str, key: str) -> str:
    path = "relay" if role == "v" else "engineer"
    return f"{config.public_base()}/app/{path}/{key}?k={token(role, key)}"
