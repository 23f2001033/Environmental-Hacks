# API v1 contract

Base path: **`/api/v1`** on the site domain (same origin as the frontend). JSON, UTF-8. Public `GET` routes need no auth. Admin routes need the header `x-admin-token` (SSM `/jalsaathi/console-token`).

**Stability rule:** fields may be added; existing fields keep their names and meaning. A breaking change means `/api/v2`.

## Public

### `GET /health`
```json
{"ok": true, "version": "0.1.0", "demo_clock": true, "bot": "Srott_bot"}
```

### `GET /config`
Settings the frontend needs at start-up. `map.style_url` is a MapLibre style (Amazon Location, key restricted to the site
domain and `http://localhost*`); it is `null` if maps are not configured, and the page must still work without a map.
```json
{"bot": "Srott_bot", "demo_clock": true,
 "map": {"style_url": "https://maps.geo.ap-south-1.amazonaws.com/v2/styles/Standard/descriptor?key=...&color-scheme=Light",
         "provider": "Amazon Location Service", "center": [78.5, 26.5], "zoom": 5}}
```

### `GET /villages`
Every village with a test on record, unsafe first.
```json
{"villages": [{"key": "412558", "name": "BEHTA LAKHI", "block": "Harpalpur", "district": "Hardoi", "state": "Uttar Pradesh",
  "lat": 27.23725, "lon": 79.77993, "geo_precision": "village", "source": "fixtures",
  "status": "unsafe", "worst_severity": "red", "open_cases": 1, "parameters": ["ecoli"]}]}
```

- `lat`/`lon` may be `null` (no trustworthy location found). `geo_precision`: `village` (geocoded and checked against the
  WQMIS district and name) or `block` (village not found; the point is the block's location; draw it differently).
- `source`: `fixtures` (the demo villages) · `snapshot` · `live`.

### `GET /villages/{key}`
Everything the village page needs.
```json
{
  "village": {"key": "412558", "name": "BEHTA LAKHI", "gram_panchayat": "BEHTA  LAKHI", "block": "Harpalpur", "block_key": "5037",
              "district": "Hardoi", "state": "Uttar Pradesh", "village_id": 412558, "block_id": 5037, "district_id": 481,
              "state_id": 31, "lat": 27.23725, "lon": 79.77993, "geo_precision": "village"},
  "status": "unsafe",
  "status_text": {"hi": "पानी असुरक्षित", "en": "Unsafe water"},
  "cases": [CaseView, ...],
  "samples": [{"parameter": "Ecoil", "value": 80, "unit": "CFU/100 ml", "acceptable_limit": 0, "permissible_limit": 0,
               "lab": null, "lab_approval": "2026-06-15T15:34:00+05:30", "sample_id": null, "source_type": "Deep Tubewell",
               "scheme_id": "20059029", "scheme_name": "BEHTA LAKHI JJM"}],
  "data_as_of": "2026-10-09",
  "source": "JJM-WQMIS, Department of Drinking Water and Sanitation, Ministry of Jal Shakti",
  "links": {"page": "https://<site>/?v=412558", "telegram_join": "https://t.me/Srott_bot?start=v_412558",
            "engineer_join": "https://t.me/Srott_bot?start=e_5037"}
}
```

`status` is one of `unsafe` · `provisional` (field kit clean, lab pending) · `safe_again` (lab re-test passed) · `unknown` (no test on record).

### `CaseView`
```json
{
  "case_id": "c-31-412558-ecoli", "code": "ecoli", "parameter": "Ecoil",
  "parameter_name": {"hi": "ई. कोलाई बैक्टीरिया", "en": "E. coli bacteria"},
  "class": "microbial", "severity": "red", "status": "AWAITING_FIX",
  "opened_at": "2026-10-09T16:20:00+00:00", "closed_at": null,
  "value": 80, "unit": "CFU/100 ml", "acceptable_limit": 0, "permissible_limit": 0,
  "lab": null, "lab_approval": "2026-06-15T15:34:00+05:30", "sample_id": null,
  "source_type": "Deep Tubewell", "scheme_id": "20059029", "scheme_name": "BEHTA LAKHI JJM",
  "advice": {"hi": ["..."], "en": ["..."]}, "actions": ["boil", "ors", "looks_clear_warning"],
  "audio_url": "https://<site>/media/audio/c-31-412558-ecoli.mp3",
  "village_key": "412558", "village": "BEHTA LAKHI", "block": "Harpalpur", "district": "Hardoi", "block_key": "5037",
  "timeline": [{"at": "...", "kind": "detected", "actor": "system", "note": "Ecoil 80 CFU/100 ml"},
               {"at": "...", "kind": "policy", "decision": "deny", "action": "close_case", "policies": [],
                "reason": "no policy permits this", "actor": "tg:12345"}]
}
```

- `severity`: `red` (act today) · `amber` (this week) · `yellow` (monitor) · `review`.
- `status`: `DETECTED` → `WARNED` → `AWAITING_FIX` (↔ `ESCALATED`) → `AWAITING_RETEST` → `PROVISIONALLY_SAFE` → `CLOSED`.
- `timeline[].kind`: `detected`, `policy`, `warned`, `awaiting_fix`, `escalated`, `fix_logged`, `awaiting_retest`, `kit_result`, `reopened`, `awaiting_lab`, `lab_result`, `closed`.
- `actions` are the advice action codes from `content/advice.json` (for icons).

### `GET /blocks/{block_key}/cases`
```json
{"block_key": "5037", "cases": [CaseView without timeline], "links": {"engineer_join": "https://t.me/Srott_bot?start=e_5037"}}
```

### `GET /cases/{case_id}`
A `CaseView` with timeline.

### `GET /stats`
```json
{"villages": 13, "villages_on_map": 11, "cases": 13, "open_cases": 13, "closed_cases": 0,
 "open_by_severity": {"red": 13}, "open_by_code": {"ecoli": 9, "nitrate": 4},
 "by_status": {"AWAITING_FIX": 13}, "by_source": {"fixtures": 13},
 "alert_latency": {"cases": 13, "median_s": 4.2, "p95_s": 9.8, "max_s": 11.0},
 "last_run": {"run_id": "...", "source": "fixtures", "records": 13, "cases_planned": 13, "new_cases": 13,
              "workflows_started": 13, "scale_run": false, "scale_execution_arn": null, "new_samples": 13, "villages": 13,
              "villages_located": 11, "geocode_calls": 15, "demo_clock": true, "data_as_of": "2026-10-09", "seconds": 4.1,
              "finished_at": "...",
              "cost_estimate": {"usd_total": 0.13, "usd_per_case": 0.0098, "usd_by_service": {"polly": 0.12, "...": 0},
                                "assumptions": {"prices": "approximate on-demand list prices ...", "...": "..."}}},
 "scale_run": {"status": "SUCCEEDED", "started": "...", "stopped": "...", "seconds": 640.2,
               "items": {"total": 580, "succeeded": 580, "failed": 0, "running": 0, "pending": 0}},
 "repeat_failures": {"question": "...", "source": "...", "totals": {"last_year": 1233, "this_year": 580, "both": 149,
                     "share_of_last_year_failing_again": 0.121}, "caveats": ["..."], "by_state_and_parameter": [...]}}
```

- `alert_latency`: seconds from case opened (failed test found) to village warned. For a scale run this includes the
  deliberate pacing (about one case a second).
- `scale_run` is `null` unless the last ingest used the ScaleRun state machine.

## Admin (header `x-admin-token`)

| Route | Body | Effect |
|---|---|---|
| `POST /admin/ingest` | `{"source": "fixtures"\|"snapshot"\|"live", "start_cases": true, "villages": ["optional names or keys"]}` | Starts the ingest asynchronously (202). Over 25 new cases go through the ScaleRun state machine |
| `POST /admin/scale-run` | `{}` | Ingests every FY 2026-27 failure in the WQMIS snapshot (about 580 cases, real deadlines) and starts their workflows at a steady pace (202) |
| `POST /admin/reset` | `{}` | Asynchronous (202): stops all workflows, deletes villages, cases, events, tokens and runs; keeps Telegram subscriptions. Takes up to a minute at scale |
| `POST /admin/restart-case` | `{"case_id"}` | Starts a fresh workflow for an existing case (for a workflow that failed) |
| `POST /admin/engineer-action` | `{"case_id", "action": "chlorination"\|"repair"\|"source_changed"\|"need_help"}` | Same as the engineer's Telegram button |
| `POST /admin/try-close` | `{"case_id"}` | An engineer tries to close without lab evidence; Cedar denies and it's logged |
| `POST /admin/kit-result` | `{"case_id", "result": "clean"\|"contaminated"}` | Same as the field-kit buttons (no photo) |
| `POST /admin/lab-result` | `{"case_id", "result": "pass"\|"fail"}` | **Simulated** lab re-test, labelled as such on the timeline |

Errors: `{"error": "..."}` with 400/401/404/405/409/500. `409` means the case isn't waiting for that step yet.
