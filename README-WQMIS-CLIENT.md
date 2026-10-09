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
