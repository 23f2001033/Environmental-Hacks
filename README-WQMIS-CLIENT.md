# Lane 1.1 — WQMIS client

This adds a defensive, standard-library HTTP/JSON client plus pytest tests.
It does **not** guess the live WQMIS endpoint. Before connecting it to production,
confirm the exact report URL, query parameters, and response/pagination shape from
a recorded successful request. The live WQMIS portal was reported as returning
HTTP 500, so tests use recorded fixtures and simulated HTTP responses only.

## Run tests (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

If `uv` is installed, the team's documented commands also work:

```powershell
uv venv
uv pip install -r requirements-dev.txt
uv run pytest -q
```

## Example (after confirming the endpoint)

```python
from jalsaathi.wqmis import WQMISClient

client = WQMISClient(
    endpoint_url="https://REPLACE-WITH-CONFIRMED-WQMIS-JSON-ENDPOINT",
    page_param="page",       # replace if the portal uses different names
    page_size_param="page_size",
    page_size=100,
)
result = client.fetch_records(previous_count=13)
if result.partial:
    # Do not resolve/close cases from this run; inspect result.warnings.
    print(result.warnings)
else:
    print(f"Fetched {len(result.records)} records across {result.pages_fetched} pages")
```

The completeness guard is a warning signal, not proof that a run is complete.

## Ingestion validation

`src/jalsaathi/ingestion.py` validates a fetched record batch before it is
passed downstream. It returns `ok` only for a non-empty batch of non-empty,
JSON-compatible dictionaries with no suspicious count drop. Empty batches are
`partial`, including when there is no previous count, because an empty response
does not establish that a water-quality case has been resolved. A zero count
or a drop greater than 50% from the previous count is also `partial`; mixed
valid and invalid records are reduced to the valid records and flagged
`partial`. If no record is valid, the result is `invalid`.

The portal's report-specific row schema is not fully confirmed. Supply
`required_fields` to `validate_ingestion` for the exact report contract that
the caller has verified; without it, validation checks basic dictionary shape
and JSON compatibility but cannot guarantee that a record is semantically
complete. Result metadata includes received/accepted/invalid counts, invalid
row indexes, and the drop fraction. Partial and invalid results explicitly
require preserving existing cases. This validation layer never resolves or
deletes cases, even for an `ok` batch. Live WQMIS connectivity remains
unverified, and successful offline tests do not verify live response shapes.

## Fetch and validate

`orchestrate_ingestion` in `src/jalsaathi/ingestion.py` adapts the existing
client methods without choosing a report, endpoint, or schema. Pass the client,
the method name (`fetch_records`, `fetch_villages`, or `fetch_samples`), and
that method's own keyword arguments. For example, `fetch_records` accepts
`params`, while portal fetches accept `parameter`, `financial_year`, and
`state_id` plus their optional filters. The adapter normalizes `records`,
`pages_fetched`, `partial`, and `warnings`, then validates the records.

Only an `ok` result contains records for normal downstream processing.
Partial/invalid results keep their warning and count metadata but return an
empty `records` list and cannot authorize case resolution or deletion. The
optional `previous_count` is supplied by the caller; this module does not
persist counts or cases. Offline tests use fake clients and do not contact
WQMIS. Live portal availability and report contracts remain unverified.
