"""Ingest Lambda: failed samples -> villages, samples and cases; starts one case workflow per new case.

event = {"source": "fixtures" | "snapshot" | "live", "start_cases": true, "villages": [optional names or keys]}
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from . import config, parse, paths, rules, store

log = logging.getLogger()
log.setLevel(logging.INFO)


def _fixture_records() -> tuple[list[dict], str]:
    with open(paths.fixtures_file("wqmis_demo_records.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    return data["records"], data.get("fetched", "")[:10] or "2026-10-09"


def _snapshot_records() -> tuple[list[dict], str]:
    s3 = config.client("s3")
    manifest = json.loads(s3.get_object(Bucket=config.bucket(), Key="data/snapshot/manifest.json")["Body"].read())
    records = []
    for f in manifest.get("files", []):
        if not f["fy"].startswith("2026"):
            continue  # cases come from the current year; last year is for analysis only
        body = json.loads(s3.get_object(Bucket=config.bucket(), Key=f"data/snapshot/{f['file']}")["Body"].read())
        for v in body["villages"]:
            for srow in v.get("samples", []) or []:
                records.append(parse.sample_from_portal(v, srow, f["param"]))
    return records, manifest.get("written_at", "")[:10]


def _live_records() -> tuple[list[dict], str]:
    from . import wqmis

    client, records = wqmis.Client(), []
    for state_id in wqmis.STATE_IDS.values():
        for para in wqmis.PARAMS:
            for v in client.villages(para, state_id, "2026-2027"):
                for srow in client.samples(para, v, "2026-2027"):
                    records.append(parse.sample_from_portal(v, srow, para))
    return records, datetime.now(timezone.utc).date().isoformat()


def load(source: str) -> tuple[list[dict], str]:
    return {"fixtures": _fixture_records, "snapshot": _snapshot_records, "live": _live_records}[source]()


def plan(records: list[dict], only: list[str] | None = None) -> list[dict]:
    """Group samples into one case per (village, contaminant); keep the worst and most recent sample."""
    cases: dict[str, dict] = {}
    for r in records:
        code = rules.param_code(r.get("parameter"))
        if not code or not r.get("village"):
            continue
        vkey = parse.village_key(r.get("state_id"), r.get("district"), r.get("block"), r.get("village"), r.get("village_id"))
        if only and vkey not in only and r["village"].lower() not in {o.lower() for o in only}:
            continue
        sev = rules.severity(code, r.get("value"), r.get("acceptable_limit"), r.get("permissible_limit"))
        if sev == "review" and r.get("value") is not None:
            continue  # within limits: not a failure
        block_key = str(r["block_id"]) if r.get("block_id") else parse.slug(r.get("state_id"), r.get("district"), r.get("block"))
        cid = rules.case_id(r.get("state_id"), vkey, code)
        candidate = {**r, "code": code, "severity": sev, "village_key": vkey, "block_key": block_key, "case_id": cid}
        best = cases.get(cid)
        samples = (best["samples"] if best else []) + [r]
        rank = (rules.SEVERITY_ORDER[sev], -(r.get("value") or 0))
        if best is None or rank < (rules.SEVERITY_ORDER[best["severity"]], -(best.get("value") or 0)):
            cases[cid] = candidate
        cases[cid]["samples"] = samples
    return list(cases.values())


def handler(event, context=None):
    event = event or {}
    source = event.get("source", "fixtures")
    started_at = time.time()
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{source}"
    records, data_as_of = load(source)
    planned = plan(records, event.get("villages"))
    sfn = config.client("stepfunctions") if event.get("start_cases", True) and config.state_machine_arn() else None
    new_cases = started = new_samples = 0

    for c in planned:
        store.put_village({"key": c["village_key"], "name": c["village"], "gram_panchayat": c.get("gram_panchayat"),
                           "block": c.get("block"), "block_key": c["block_key"], "district": c.get("district"),
                           "state": c.get("state"), "village_id": c.get("village_id"), "block_id": c.get("block_id"),
                           "district_id": c.get("district_id"), "state_id": c.get("state_id"),
                           "lat": c.get("lat"), "lon": c.get("lon"), "data_as_of": data_as_of})
        for s in c["samples"]:
            new_samples += store.put_sample(c["village_key"], {k: v for k, v in s.items() if k not in ("raw_source",)})
        case = {k: c.get(k) for k in ("case_id", "code", "parameter", "severity", "village_key", "block_key", "village", "block",
                                     "district", "state", "value", "unit", "acceptable_limit", "permissible_limit", "lab",
                                     "lab_approval", "sample_id", "source_type", "scheme_id", "scheme_name")}
        case.update(status="DETECTED", opened_at=store.now_iso(), source=source, timers=rules.timers(c["severity"], config.demo_clock()))
        if store.create_case(case):
            new_cases += 1
            if sfn:
                sfn.start_execution(stateMachineArn=config.state_machine_arn(),
                                    name=f"{c['case_id']}-{uuid.uuid4().hex[:6]}"[:80],
                                    input=json.dumps({"case_id": c["case_id"], "timers": case["timers"]}))
                started += 1

    run = {"run_id": run_id, "source": source, "records": len(records), "cases_planned": len(planned),
           "new_cases": new_cases, "workflows_started": started, "new_samples": new_samples, "data_as_of": data_as_of,
           "seconds": round(time.time() - started_at, 2), "finished_at": store.now_iso()}
    store.put_run(run)
    log.info("ingest done %s", run)
    return run
