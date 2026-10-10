"""Turn WQMIS portal rows into clean sample records."""

from __future__ import annotations

import re
from datetime import datetime

_SOURCE_TYPE = re.compile(r"Source type\s*:\s*([^\]]+?)\s*\]")
_SCHEME = re.compile(r"schemeId\s*:\s*(\d+)\s*,\s*scheme name\s*:\s*(.*?)\s*,\s*Type\s*:\s*([A-Za-z-]+)")
_LOCATION = re.compile(r"Location\s*:\s*(.*?)\s*\[")
_VALUE = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)\s*(?:\((.*?)\))?\s*$")
_SLUG = re.compile(r"[^a-z0-9]+")


def slug(*parts: object) -> str:
    text = "-".join(str(p) for p in parts if p not in (None, ""))
    return _SLUG.sub("-", text.lower()).strip("-")


def parse_source(text: str | None) -> dict:
    """Parse 'Location : X [ Source type : Deep Tubewell ] [ schemeId : 1, scheme name : Y, Type : PWS ]'."""
    text = text or ""
    out = {"location": None, "source_type": None, "scheme_id": None, "scheme_name": None, "pws": None}
    if m := _LOCATION.search(text):
        out["location"] = m.group(1).strip() or None
    if m := _SOURCE_TYPE.search(text):
        out["source_type"] = m.group(1).strip() or None
    if m := _SCHEME.search(text):
        out["scheme_id"] = m.group(1)
        out["scheme_name"] = m.group(2).strip() or None
        out["pws"] = m.group(3).strip().upper() == "PWS"
    return out


def parse_value(text: str | None) -> tuple[float | None, str | None]:
    """'50.000 (CFU/100 ml)' -> (50.0, 'CFU/100 ml'). Unparseable -> (None, None)."""
    if text is None:
        return None, None
    m = _VALUE.match(str(text))
    if not m:
        return None, None
    return float(m.group(1)), (m.group(2).strip() if m.group(2) else None)


def parse_limit(text: object) -> float | None:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def parse_approval(text: str | None) -> str | None:
    """'21/08/2026 13:57:00' (IST) -> '2026-08-21T13:57:00+05:30'."""
    if not text:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(text).strip(), fmt).strftime("%Y-%m-%dT%H:%M:%S+05:30")
        except ValueError:
            continue
    return None


def village_key(state_id, district, block, village, village_id) -> str:
    """Stable key for a village: the WQMIS village ID when we have it, otherwise a slug of the names."""
    if village_id not in (None, "", 0):
        return str(village_id)
    return slug(state_id, district, block, village)


def sample_from_portal(village_row: dict, sample_row: dict, param: str) -> dict:
    """Combine a ContaminantwiseVillagefil row and a Contaminantwisesamplefillist row into one sample record."""
    src = parse_source(sample_row.get("sample_sourceName"))
    value, unit = parse_value(sample_row.get("Parametervalue"))
    return {
        "state": village_row.get("State"),
        "state_id": village_row.get("StateId"),
        "district": village_row.get("District"),
        "district_id": village_row.get("DistrictId"),
        "block": village_row.get("Block"),
        "block_id": village_row.get("BlockId"),
        "gram_panchayat": village_row.get("Grampanchayat"),
        "gram_panchayat_id": village_row.get("GrampanchayatId"),
        "village": village_row.get("Village"),
        "village_id": village_row.get("VillageId"),
        "parameter": param,
        "value": value,
        "unit": unit,
        "acceptable_limit": parse_limit(sample_row.get("Acceptablelimit")),
        "permissible_limit": parse_limit(sample_row.get("Permissiblelimit")),
        "lab": (sample_row.get("labname") or "").strip() or None,
        "lab_approval": parse_approval(sample_row.get("s_report_approval_action_time")),
        "sample_id": sample_row.get("SampleId"),
        "raw_source": sample_row.get("sample_sourceName"),
        "raw_value": sample_row.get("Parametervalue"),
        **{k: src[k] for k in ("source_type", "scheme_id", "scheme_name", "pws")},
    }
