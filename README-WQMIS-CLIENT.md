# Lane 1.1 — WQMIS Client

This contribution provides two WQMIS-related clients with defensive handling and automated tests.

## Clients

* **Generic JSON client:** `src/jalsaathi/wqmis.py` provides configurable HTTP/JSON requests, retries, pagination, and completeness warnings. Its endpoint and pagination parameters must be confirmed before production use.
* **Portal-specific client:** `src/jalsaathi/wqmis_portal.py` implements the public JJM-WQMIS contaminant-report requests, encrypted parameters, session handling, pagination, and sample-value parsing.

## Important limitations

The live portal has been reported to return HTTP 500 errors for some requests. Automated tests use mocked HTTP responses and do not establish that every live endpoint works.

Before production ingestion, verify the endpoint contracts and response shapes against successful recorded requests. Treat empty or suspiciously reduced results as potentially incomplete, not as proof that a water-quality issue has been resolved.

Callers should preserve existing cases and raise an appropriate warning when a result is marked partial.

## Run tests (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

If `uv` is installed:

```powershell
uv venv
uv pip install -r requirements-dev.txt
uv run pytest -q
```

## Generic client example

Use only after confirming the exact JSON endpoint and pagination contract.

```python
from jalsaathi.wqmis import WQMISClient

client = WQMISClient(
    endpoint_url="https://REPLACE-WITH-CONFIRMED-ENDPOINT",
    page_param="page",
    page_size_param="page_size",
    page_size=100,
)

result = client.fetch_records(previous_count=13)
if result.partial:
    # Do not resolve/close cases from this run; inspect result.warnings.
    print(result.warnings)
else:
    print(
        f"Fetched {len(result.records)} records "
        f"across {result.pages_fetched} pages"
    )

The completeness guard is a warning signal, not proof that a run is complete. Live portal connectivity and production readiness remain unverified.

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
