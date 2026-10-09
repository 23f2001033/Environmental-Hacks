import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from jalsaathi.wqmis import WQMISClient, WQMISClientError


def make_client(responses, *, page_size=2, max_retries=0, sleep=lambda _: None):
    calls = []

    def transport(url, timeout):
        calls.append(url)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return json.dumps(item).encode("utf-8")

    client = WQMISClient(
        "https://example.test/report",
        page_size=page_size,
        max_retries=max_retries,
        transport=transport,
        sleep=sleep,
    )
    return client, calls


def test_extracts_records_from_project_fixture():
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "fixtures"
        / "wqmis_demo_records.json"
    )
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    records = WQMISClient.extract_records(data)
    assert len(records) == 13
    assert records[0]["village"] == "BEHTA LAKHI"
    assert records[0]["parameter"] == "Ecoil"


def test_paginates_until_short_page():
    client, calls = make_client(
        [
            {"records": [{"id": 1}, {"id": 2}]},
            {"records": [{"id": 3}]},
        ],
        page_size=2,
    )
    result = client.fetch_records()
    assert [r["id"] for r in result.records] == [1, 2, 3]
    assert result.pages_fetched == 2
    assert len(calls) == 2
    assert "page=1" in calls[0]
    assert "page=2" in calls[1]


def test_uses_pagination_metadata_even_for_short_page():
    client, _ = make_client(
        [
            {"records": [{"id": 1}], "total_pages": 2},
            {"records": [{"id": 2}], "total_pages": 2},
        ],
        page_size=10,
    )
    result = client.fetch_records()
    assert [r["id"] for r in result.records] == [1, 2]
    assert result.pages_fetched == 2


def test_retries_http_500_then_succeeds():
    error = HTTPError(
        "https://example.test/report?page=1&page_size=2",
        500,
        "server error",
        hdrs=None,
        fp=None,
    )
    client, calls = make_client(
        [error, {"records": [{"id": 1}]}],
        page_size=2,
        max_retries=1,
    )
    result = client.fetch_records()
    assert result.records == [{"id": 1}]
    assert len(calls) == 2


def test_non_retryable_http_error_fails_immediately():
    error = HTTPError(
        "https://example.test/report?page=1&page_size=2",
        404,
        "not found",
        hdrs=None,
        fp=None,
    )
    client, calls = make_client([error], max_retries=3)
    with pytest.raises(WQMISClientError, match="non-retryable HTTP 404"):
        client.fetch_records()
    assert len(calls) == 1


def test_zero_records_after_nonempty_run_is_flagged_partial():
    client, _ = make_client([{"records": []}], page_size=2)
    result = client.fetch_records(previous_count=13)
    assert result.partial is True
    assert any("0 records" in warning for warning in result.warnings)


def test_drop_over_50_percent_is_flagged_partial():
    client, _ = make_client([{"records": [{"id": 1}, {"id": 2}]}], page_size=10)
    result = client.fetch_records(previous_count=10)
    assert result.partial is True
    assert any("50%" in warning for warning in result.warnings)


def test_invalid_endpoint_is_rejected():
    with pytest.raises(ValueError, match="http"):
        WQMISClient("not-a-url")


def test_invalid_json_is_reported():
    client = WQMISClient(
        "https://example.test/report",
        transport=lambda url, timeout: b"<html>not json</html>",
        max_retries=0,
    )
    with pytest.raises(WQMISClientError, match="invalid JSON"):
        client.fetch_records()
