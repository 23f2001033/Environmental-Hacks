"""Ingest Lambda: failed samples -> villages, samples and cases; starts one case workflow per new case.

event = {"source": "fixtures" | "snapshot" | "live", "start_cases": true, "villages": [optional names or keys],
         "scale": optional bool, "geocode": optional bool, "demo_clock": optional bool}
event = {"action": "reset"} stops all workflows and deletes demo data (too slow for the 29 s API limit at scale).

Small runs start workflows directly. Large runs (or scale=true) hand the list to the ScaleRun state machine, which
starts them at a steady pace so a new account's Lambda concurrency limit of 10 is not swamped.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from . import config, costs, geo, parse, paths, rules, store

log = logging.getLogger()
log.setLevel(logging.INFO)

SCALE_THRESHOLD = 25
SCALE_ITEMS_KEY = "runs/scale-items.json"
GEO_FIELDS = ("lat", "lon", "geo_precision", "geo_title")


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


def use_demo_clock(source: str, event: dict) -> bool:
    """Minutes-long deadlines only for the demo fixtures; real WQMIS cases get real deadlines (48 h, 7 days...)."""
    if "demo_clock" in event:
        return bool(event["demo_clock"])
    return source == "fixtures" and config.demo_clock()


def exec_name(case_id: str, run_id: str) -> str:
    """Deterministic workflow name, so a retried scale-run item can never start a case twice."""
    digest = hashlib.sha1(case_id.encode()).hexdigest()[:8]
    return f"{case_id[:50]}-{digest}-{run_id[:15]}"


def scale_items(cases: list[dict], run_id: str) -> list[dict]:
    return [{"case_id": c["case_id"], "timers": c["timers"], "exec_name": exec_name(c["case_id"], run_id)} for c in cases]


def _start_scale_run(items: list[dict], run_id: str) -> str:
    sfn = config.client("stepfunctions")
    running = sfn.list_executions(stateMachineArn=config.scale_run_arn(), statusFilter="RUNNING", maxResults=1)["executions"]
    if running:
        raise RuntimeError("a scale run is already in progress: " + running[0]["name"])
    config.client("s3").put_object(Bucket=config.bucket(), Key=SCALE_ITEMS_KEY, Body=json.dumps(items).encode(),
                                   ContentType="application/json")
    return sfn.start_execution(stateMachineArn=config.scale_run_arn(), name=run_id,
                               input=json.dumps({"run_id": run_id, "items": len(items)}))["executionArn"]


def _stop_all(arn: str) -> int:
    from botocore.exceptions import ClientError

    if not arn:
        return 0
    sfn, stopped = config.client("stepfunctions"), 0
    for page in sfn.get_paginator("list_executions").paginate(stateMachineArn=arn, statusFilter="RUNNING"):
        for ex in page["executions"]:
            for attempt in range(6):
                try:
                    sfn.stop_execution(executionArn=ex["executionArn"], cause="demo reset")
                    stopped += 1
                    break
                except ClientError as exc:
                    if exc.response["Error"]["Code"] != "ThrottlingException":
                        raise
                    time.sleep(0.5 * (attempt + 1))
    return stopped


def reset() -> dict:
    stopped = _stop_all(config.scale_run_arn()) + _stop_all(config.state_machine_arn())
    result = {"workflows_stopped": stopped, "deleted": store.reset_demo(), "finished_at": store.now_iso()}
    log.info("reset done %s", result)
    return result


def village_item(c: dict, data_as_of: str, source: str, existing: dict | None) -> dict:
    v = {"key": c["village_key"], "name": c["village"], "gram_panchayat": c.get("gram_panchayat"), "block": c.get("block"),
         "block_key": c["block_key"], "district": c.get("district"), "state": c.get("state"),
         "village_id": c.get("village_id"), "block_id": c.get("block_id"), "district_id": c.get("district_id"),
         "state_id": c.get("state_id"), "lat": c.get("lat"), "lon": c.get("lon"), "data_as_of": data_as_of,
         "source": source}
    if existing:
        v.update({k: existing[k] for k in GEO_FIELDS if existing.get(k) is not None and v.get(k) is None})
        if existing.get("source") == "fixtures":
            v["source"] = "fixtures"  # demo villages stay first in the bot's picker
    return v


def handler(event, context=None):
    event = event or {}
    if event.get("action") == "reset":
        return reset()
    source = event.get("source", "fixtures")
    started_at = time.time()
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{source}"
    records, data_as_of = load(source)
    planned = plan(records, event.get("villages"))
    demo = use_demo_clock(source, event)
    start = event.get("start_cases", True) and bool(config.state_machine_arn())
    new_cases, new_samples, geocodes, located, block_cache, villages = [], 0, 0, 0, {}, {}

    for c in planned:
        vkey = c["village_key"]
        if vkey not in villages:
            village = village_item(c, data_as_of, source, store.get_village(vkey))
            if village.get("lat") is None and event.get("geocode", True):
                found, calls = geo.locate(c["village"], c.get("block"), c.get("district"), c.get("state"), block_cache)
                village.update(found)
                geocodes += calls
            located += village.get("lat") is not None
            store.put_village(village)
            villages[vkey] = village
        for s in c["samples"]:
            new_samples += store.put_sample(vkey, {k: v for k, v in s.items() if k not in ("raw_source",)})
        case = {k: c.get(k) for k in ("case_id", "code", "parameter", "severity", "village_key", "block_key", "village", "block",
                                     "district", "state", "value", "unit", "acceptable_limit", "permissible_limit", "lab",
                                     "lab_approval", "sample_id", "source_type", "scheme_id", "scheme_name")}
        case.update(status="DETECTED", opened_at=store.now_iso(), source=source, timers=rules.timers(c["severity"], demo))
        if store.create_case(case):
            new_cases.append(case)

    started, scale_arn = 0, None
    if start and new_cases:
        if event.get("scale", len(new_cases) > SCALE_THRESHOLD) and config.scale_run_arn():
            scale_arn = _start_scale_run(scale_items(new_cases, run_id), run_id)
        else:
            sfn = config.client("stepfunctions")
            for case in new_cases:
                sfn.start_execution(stateMachineArn=config.state_machine_arn(),
                                    name=f"{case['case_id']}-{uuid.uuid4().hex[:6]}"[:80],
                                    input=json.dumps({"case_id": case["case_id"], "timers": case["timers"]}))
                started += 1

    audio = len(new_cases) if source == "fixtures" else 0
    run = {"run_id": run_id, "source": source, "records": len(records), "cases_planned": len(planned),
           "new_cases": len(new_cases), "workflows_started": started, "scale_run": bool(scale_arn),
           "scale_execution_arn": scale_arn, "new_samples": new_samples, "villages": len(villages),
           "villages_located": located, "geocode_calls": geocodes, "demo_clock": demo, "data_as_of": data_as_of,
           "seconds": round(time.time() - started_at, 2), "finished_at": store.now_iso(),
           "cost_estimate": costs.estimate(len(new_cases), audio, geocodes, len(new_cases) if scale_arn else 0)}
    store.put_run(run)
    log.info("ingest done %s", {k: v for k, v in run.items() if k != "cost_estimate"})
    return run
