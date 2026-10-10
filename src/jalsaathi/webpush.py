"""Web Push to the JalSaathi web app, written against the standards (RFC 8291 encryption, RFC 8292 VAPID).

No push library: the usual one needs a package with no Lambda wheel. This is about 60 lines on `cryptography`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RECORD_SIZE = 4096


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _hkdf(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:length]


def public_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def private_from_b64(text: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(unb64u(text), "big"), ec.SECP256R1())


def new_vapid_private() -> str:
    """A new VAPID private key as base64url (store it in SSM)."""
    return b64u(ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value.to_bytes(32, "big"))


def encrypt(payload: bytes, p256dh: str, auth: str, salt: bytes | None = None,
            server_key: ec.EllipticCurvePrivateKey | None = None) -> bytes:
    """aes128gcm body for one subscription (RFC 8291 section 3.4 / RFC 8188)."""
    ua_public = unb64u(p256dh)
    server_key = server_key or ec.generate_private_key(ec.SECP256R1())
    as_public = public_bytes(server_key)
    shared = server_key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = _hkdf(unb64u(auth), shared, b"WebPush: info\x00" + ua_public + as_public, 32)
    salt = salt or os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    body = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack(">IB", RECORD_SIZE, len(as_public)) + as_public + body


def vapid_header(endpoint: str, private_b64: str, subject: str) -> str:
    key = private_from_b64(private_b64)
    aud = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(endpoint))
    head = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    claims = b64u(json.dumps({"aud": aud, "exp": int(time.time()) + 12 * 3600, "sub": subject}).encode())
    r, s = decode_dss_signature(key.sign(f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256())))
    jwt = f"{head}.{claims}.{b64u(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    return f"vapid t={jwt}, k={b64u(public_bytes(key))}"


@lru_cache(maxsize=1)
def public_key() -> str | None:
    """The VAPID public key the browser needs to subscribe (derived from the private key in SSM)."""
    from . import config

    try:
        return b64u(public_bytes(private_from_b64(config.secret(config.SSM_VAPID_PRIVATE))))
    except Exception:  # noqa: BLE001 - push is optional
        return None


def send(subscription: dict, message: dict, ttl: int = 86400) -> int:
    """POST one encrypted message. Returns the push service's HTTP status (201 = accepted; 404/410 = gone)."""
    from . import config

    keys = subscription["keys"]
    body = encrypt(json.dumps(message, ensure_ascii=False).encode(), keys["p256dh"], keys["auth"])
    req = urllib.request.Request(subscription["endpoint"], data=body, method="POST", headers={
        "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", "TTL": str(ttl), "Urgency": "high",
        "Authorization": vapid_header(subscription["endpoint"], config.secret(config.SSM_VAPID_PRIVATE),
                                      config.public_base() or "https://jalsaathi.example"),
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
