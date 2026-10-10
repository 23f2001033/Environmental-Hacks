"""Read models shared by the web API and the bot, so the page and Telegram always say the same thing."""

from __future__ import annotations

from . import advice, config, rules, store, voice

STATUS_TEXT = {
    "unsafe": {"hi": "पानी असुरक्षित", "en": "Unsafe water"},
    "provisional": {"hi": "फील्ड जांच साफ़, लैब पुष्टि बाकी", "en": "Field test clean, lab confirmation pending"},
    "safe_again": {"hi": "दोबारा जांच में पानी सुरक्षित", "en": "Safe again after re-test"},
    "unknown": {"hi": "कोई जांच रिकॉर्ड नहीं", "en": "No test on record"},
}


def village_status(cases: list[dict]) -> str:
    if not cases:
        return "unknown"
    open_cases = [c for c in cases if c.get("status") in store.OPEN_STATUSES]
    if not open_cases:
        return "safe_again"
    if all(c.get("status") == "PROVISIONALLY_SAFE" for c in open_cases):
        return "provisional"
    return "unsafe"


def case_view(case: dict, with_timeline: bool = True) -> dict:
    code = case["code"]
    view = {
        "case_id": case["case_id"],
        "code": code,
        "parameter": case.get("parameter"),
        "parameter_name": {"hi": advice.name(code, "hi"), "en": advice.name(code, "en")},
        "class": rules.contaminant_class(code),
        "severity": case.get("severity"),
        "status": case.get("status"),
        "opened_at": case.get("opened_at"),
        "warned_at": case.get("warned_at"),
        "closed_at": case.get("closed_at"),
        "deadline_at": case.get("deadline_at"),
        "escalations": case.get("escalations", 0),
        "source": case.get("source"),
        "value": case.get("value"),
        "unit": case.get("unit"),
        "acceptable_limit": case.get("acceptable_limit"),
        "permissible_limit": case.get("permissible_limit"),
        "lab": case.get("lab"),
        "lab_approval": case.get("lab_approval"),
        "sample_id": case.get("sample_id"),
        "source_type": case.get("source_type"),
        "scheme_id": case.get("scheme_id"),
        "scheme_name": case.get("scheme_name"),
        "advice": {"hi": advice.lines(code, "hi"), "en": advice.lines(code, "en")},
        "actions": advice.actions(code),
        "engineer_fix": (advice.entry(code) or {}).get("engineer_fix"),
        "audio_url": voice.public_url(case.get("audio_path")),
        "audio": {"hi": voice.public_url(case.get("audio_path")), "en": voice.public_url(case.get("audio_path_en"))},
        "village_key": case.get("village_key"),
        "village": case.get("village"),
        "block": case.get("block"),
        "district": case.get("district"),
        "block_key": case.get("block_key"),
    }
    if with_timeline:
        view["timeline"] = [
            {k: e.get(k) for k in ("at", "kind", "actor", "note", "decision", "policies", "reason", "action", "result")
             if e.get(k) is not None}
            for e in store.events(case["case_id"])
        ]
    return view


def village_bundle(key: str, make_audio: bool = False) -> dict | None:
    items = store.village_items(key)
    meta = next((i for i in items if i["sk"] == "META"), None)
    if not meta:
        return None
    case_ids = [i["case_id"] for i in items if i["sk"].startswith("CASEREF#")]
    cases = [c for c in (store.get_case(cid) for cid in case_ids) if c]
    cases.sort(key=lambda c: (rules.SEVERITY_ORDER.get(c.get("severity"), 9), c.get("opened_at", "")))
    if make_audio:
        for c in cases:
            if c.get("status") in store.OPEN_STATUSES:
                voice.ensure_audio(c)  # first visit makes the voice notes; later visits reuse them
                voice.ensure_audio(c, "en")
    status = village_status(cases)
    samples = [{k: s.get(k) for k in ("parameter", "value", "unit", "acceptable_limit", "permissible_limit", "lab",
                                       "lab_approval", "sample_id", "source_type", "scheme_id", "scheme_name")}
               for s in items if s["sk"].startswith("SAMPLE#")]
    return {
        "village": {k: meta.get(k) for k in ("key", "name", "gram_panchayat", "block", "block_key", "district", "state",
                                             "village_id", "block_id", "district_id", "state_id", "lat", "lon",
                                             "geo_precision")},
        "status": status,
        "status_text": STATUS_TEXT[status],
        "cases": [case_view(c) for c in cases],
        "samples": samples,
        "data_as_of": meta.get("data_as_of"),
        "source": "JJM-WQMIS, Department of Drinking Water and Sanitation, Ministry of Jal Shakti",
        "links": {"page": config.village_url(key), "telegram_join": config.join_link("v", key),
                  "engineer_join": config.join_link("e", meta.get("block_key", ""))},
    }


def village_summary(meta: dict, cases: list[dict]) -> dict:
    status = village_status(cases)
    worst = min((rules.SEVERITY_ORDER.get(c.get("severity"), 9) for c in cases if c.get("status") in store.OPEN_STATUSES),
                default=None)
    return {"key": meta["key"], "name": meta.get("name"), "block": meta.get("block"), "district": meta.get("district"),
            "state": meta.get("state"), "lat": meta.get("lat"), "lon": meta.get("lon"),
            "geo_precision": meta.get("geo_precision"), "source": meta.get("source"), "status": status,
            "worst_severity": next((s for s, o in rules.SEVERITY_ORDER.items() if o == worst), None),
            "open_cases": sum(1 for c in cases if c.get("status") in store.OPEN_STATUSES),
            "parameters": sorted({c["code"] for c in cases})}
