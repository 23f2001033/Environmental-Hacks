# API v1 contract

Base path: **`/api/v1`** on the site domain (same origin as the frontend). JSON, UTF-8. Public `GET` routes need no auth. Admin routes need the header `x-admin-token` (SSM `/jalsaathi/console-token`).

**Stability rule:** fields may be added; existing fields keep their names and meaning. A breaking change means `/api/v2`.

## Public

### `GET /health`
```json
{"ok": true, "version": "0.1.0", "demo_clock": true, "bot": "Srott_bot"}
```

### `GET /villages`
Every village with a test on record, unsafe first.
```json
{"villages": [{"key": "412558", "name": "BEHTA LAKHI", "block": "Harpalpur", "district": "Hardoi", "state": "Uttar Pradesh",
  "lat": null, "lon": null, "status": "unsafe", "worst_severity": "red", "open_cases": 1, "parameters": ["ecoli"]}]}
```

### `GET /villages/{key}`
Everything the village page needs.
```json
{
  "village": {"key": "412558", "name": "BEHTA LAKHI", "gram_panchayat": "BEHTA  LAKHI", "block": "Harpalpur", "block_key": "5037",
              "district": "Hardoi", "state": "Uttar Pradesh", "village_id": 412558, "block_id": 5037, "district_id": 481,
              "state_id": 31, "lat": null, "lon": null},
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
{"villages": 13, "cases": 13, "open_cases": 13, "closed_cases": 0,
 "open_by_severity": {"red": 13}, "open_by_code": {"ecoli": 9, "nitrate": 4},
 "by_status": {"AWAITING_FIX": 13}, "last_run": {"run_id": "...", "source": "fixtures", "records": 13, "cases_planned": 13,
 "new_cases": 13, "workflows_started": 13, "data_as_of": "2026-10-09", "seconds": 4.1, "finished_at": "..."}}
```

## Admin (header `x-admin-token`)

| Route | Body | Effect |
|---|---|---|
| `POST /admin/ingest` | `{"source": "fixtures"\|"snapshot"\|"live", "start_cases": true, "villages": ["optional names or keys"]}` | Starts the ingest asynchronously (202) |
| `POST /admin/reset` | `{}` | Deletes demo villages, cases, events and tokens; keeps Telegram subscriptions |
| `POST /admin/engineer-action` | `{"case_id", "action": "chlorination"\|"repair"\|"source_changed"\|"need_help"}` | Same as the engineer's Telegram button |
| `POST /admin/try-close` | `{"case_id"}` | An engineer tries to close without lab evidence; Cedar denies and it's logged |
| `POST /admin/kit-result` | `{"case_id", "result": "clean"\|"contaminated"}` | Same as the field-kit buttons (no photo) |
| `POST /admin/lab-result` | `{"case_id", "result": "pass"\|"fail"}` | **Simulated** lab re-test, labelled as such on the timeline |

Errors: `{"error": "..."}` with 400/401/404/405/409/500. `409` means the case isn't waiting for that step yet.
