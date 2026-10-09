"""Village coordinates from Amazon Location (geo-places Geocode), validated against the WQMIS district.

The geocoder happily returns a same-named place in another district, or a shop. A result is accepted only when its
district matches and its name matches the village; otherwise we fall back to the block, and say so (geo_precision).
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher

from . import config

log = logging.getLogger()

REJECT_TYPES = {"PointOfInterest", "Street", "Intersection", "PointAddress", "InterpolatedAddress"}


def norm(text: str | None) -> str:
    return re.sub(r"[^a-z]", "", (text or "").lower())


def similar(a: str | None, b: str | None, threshold: float = 0.8) -> bool:
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a)) or SequenceMatcher(None, a, b).ratio() >= threshold


def _district_of(item: dict) -> str:
    return ((item.get("Address") or {}).get("SubRegion") or {}).get("Name", "")


def pick(items: list[dict], name: str, district: str, need_name: bool = True) -> dict | None:
    """First result in the right district (and, for villages, with the right name and a place-like type)."""
    for item in items:
        if item.get("PlaceType") in REJECT_TYPES or not similar(_district_of(item), district, 0.75):
            continue
        title = (item.get("Title") or "").split(",")[0]
        if need_name and not similar(title, name):
            continue
        lon, lat = item["Position"]
        return {"lat": round(lat, 5), "lon": round(lon, 5), "geo_title": item.get("Title")}
    return None


def _geocode(query: str) -> list[dict]:
    resp = config.client("geo-places").geocode(QueryText=query, MaxResults=3, IntendedUse="Storage",
                                                Filter={"IncludeCountries": ["IND"]})
    return resp.get("ResultItems", [])


def locate(village: str, block: str | None, district: str | None, state: str | None, block_cache: dict) -> tuple[dict, int]:
    """(location fields, geocode calls made). Location is {} when nothing trustworthy was found."""
    calls = 0
    try:
        calls += 1
        hit = pick(_geocode(", ".join(p for p in (village, block, district, state, "India") if p)), village, district or "")
        if hit:
            return {**hit, "geo_precision": "village"}, calls
        bkey = f"{state}|{district}|{block}"
        if bkey not in block_cache:
            calls += 1
            block_cache[bkey] = pick(_geocode(", ".join(p for p in (block, district, state, "India") if p)), block or "",
                                     district or "", need_name=False)
        if block_cache[bkey]:
            return {**block_cache[bkey], "geo_precision": "block"}, calls
    except Exception as exc:  # noqa: BLE001 - a missing map pin must never stop ingest
        log.warning("geocode failed for %s: %s", village, exc)
    return {}, calls
