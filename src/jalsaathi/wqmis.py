"""JJM-WQMIS client: replicates the portal's own browser calls, politely (DECISIONS.md D-17).

The portal encrypts query parameters in the browser with AES-128-CBC; key and IV come from its public frmValidate.js.
"""

from __future__ import annotations

import base64
import http.cookiejar
import json
import time
import urllib.parse
import urllib.request

BASE = "https://ejalshakti.gov.in/WQMIS"
_KEY = b"8080808080808080"
STATE_IDS = {"Uttar Pradesh": 31, "Rajasthan": 27}
PARAMS = ["Ecoil", "Coliform", "Nitrate", "Fluoride", "Total arsenic"]


def enc(value) -> str:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

    return base64.b64encode(AES.new(_KEY, AES.MODE_CBC, _KEY).encrypt(pad(str(value).encode(), 16))).decode()


class Client:
    def __init__(self, pause: float = 1.0, tries: int = 4, timeout: int = 90):
        self.pause, self.tries, self.timeout = pause, tries, timeout
        self.opener = None

    def _open_session(self, para: str, state_id: int, fy: str) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.opener.addheaders = [("User-Agent", "Mozilla/5.0 (JalSaathi; hackathon research)")]
        q = {"paraname": enc(para), "fy": enc(fy), "stid": enc(state_id), "dtid": enc(0), "blid": enc(0),
             "gpid": enc(0), "villid": enc(0)}
        self.opener.open(f"{BASE}/Report/Contaminantwisesamplelist?{urllib.parse.urlencode(q)}", timeout=self.timeout).read()
        self.opener.addheaders += [("X-Requested-With", "XMLHttpRequest"), ("Referer", f"{BASE}/Report/Contaminantwisesamplelist")]

    def _post(self, path: str, fields: dict) -> list[dict]:
        data = urllib.parse.urlencode({k: enc(v) for k, v in fields.items()}).encode()
        last = None
        for attempt in range(self.tries):
            try:
                body = self.opener.open(f"{BASE}{path}", data, timeout=self.timeout).read()
                return json.loads(body)["Contaminantwise"]
            except Exception as exc:  # noqa: BLE001 - the portal fails in many ways; retry them all
                last = exc
                time.sleep(self.pause * 10 * (attempt + 1))
        raise RuntimeError(f"WQMIS {path} failed after {self.tries} tries: {last}")

    def villages(self, para: str, state_id: int, fy: str) -> list[dict]:
        self._open_session(para, state_id, fy)
        out, page = [], 1
        while page <= 200:
            rows = self._post("/Report/ContaminantwiseVillagefil/",
                              dict(cpage=page, paraname=para, stid=state_id, dtid=0, blid=0, gpid=0, villid=0, fy=fy))
            if not rows:
                break
            out += rows
            page += 1
            time.sleep(self.pause)
        return out

    def samples(self, para: str, village_row: dict, fy: str) -> list[dict]:
        rows = self._post("/Report/Contaminantwisesamplefillist/",
                          dict(cpage=1, paraname=para, stid=village_row["StateId"], dtid=village_row["DistrictId"],
                               villid=village_row["VillageId"], fy=fy))
        time.sleep(self.pause)
        return rows


def guard(previous: dict[str, int], current: dict[str, int]) -> list[str]:
    """Return keys whose count collapsed (to zero, or by more than half). A collapse means a partial portal response."""
    suspicious = []
    for key, before in previous.items():
        after = current.get(key, 0)
        if before > 0 and (after == 0 or after < before / 2):
            suspicious.append(key)
    return suspicious
