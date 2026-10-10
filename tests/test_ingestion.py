import math
from dataclasses import dataclass, field

import pytest

from jalsaathi.ingestion import orchestrate_ingestion, validate_ingestion


@dataclass
class FakeFetchResult:
    records: object
    pages_fetched: int = 1
    partial: bool = False
    warnings: list[str] = field(default_factory=list)


class FakeGenericClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.call_kwargs = None

    def fetch_records(self, **kwargs):
        self.call_kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


class FakePortalClient:
    def __init__(self, result):
        self.result = result
        self.call_kwargs = None

    def fetch_samples(self, **kwargs):
        self.call_kwargs = kwargs
        return self.result


class RaisingFetchResult:
    def __init__(self, failing_attribute):
        self.failing_attribute = failing_attribute

    def _read(self, name, value):
        if self.failing_attribute == name:
            raise RuntimeError(f"failed reading {name}")
        return value

    @property
    def records(self):
        return self._read("records", [{"sample_id": "S-1"}])

    @property
    def pages_fetched(self):
        return self._read("pages_fetched", 1)

    @property
    def partial(self):
        return self._read("partial", False)

    @property
    def warnings(self):
        return self._read("warnings", [])


def test_valid_nonempty_batch_is_ok_and_keeps_records():
    records = [{"village_id": 17, "parameter": "Nitrate", "value": 0}]
    result = validate_ingestion(records, previous_count=1)

    assert result.status == "ok"
    assert result.records == records
    assert result.previous_count == 1
    assert result.current_count == 1
    assert result.accepted_count == 1
    assert result.invalid_count == 0
    assert result.drop_fraction is None
    assert result.preserve_existing_cases is False
    assert result.cases_may_be_resolved is False


def test_report_specific_required_fields_accept_valid_false_and_zero_values():
    result = validate_ingestion(
        [{"sample_id": "S-1", "value": 0, "pws": False}],
        required_fields=["sample_id", "value", "pws"],
    )

    assert result.status == "ok"
    assert result.records == [{"sample_id": "S-1", "value": 0, "pws": False}]


def test_empty_batch_is_partial_even_without_a_previous_count():
    result = validate_ingestion([])

    assert result.status == "partial"
    assert result.current_count == 0
    assert result.accepted_count == 0
    assert result.preserve_existing_cases is True
    assert result.cases_may_be_resolved is False
    assert "empty batch" in result.message


def test_empty_batch_after_existing_records_is_partial_with_full_drop_metadata():
    result = validate_ingestion([], previous_count=8)

    assert result.status == "partial"
    assert result.previous_count == 8
    assert result.current_count == 0
    assert result.drop_fraction == 1.0
    assert result.preserve_existing_cases is True
    assert "zero records" in result.message


@pytest.mark.parametrize(
    ("current_count", "expected_status", "expected_drop"),
    [(4, "partial", 0.6), (5, "ok", 0.5), (6, "ok", 0.4)],
)
def test_count_drop_boundary(current_count, expected_status, expected_drop):
    result = validate_ingestion(
        [{"record_id": index} for index in range(current_count)], previous_count=10
    )

    assert result.status == expected_status
    assert result.drop_fraction == expected_drop
    assert result.preserve_existing_cases is (expected_status != "ok")


@pytest.mark.parametrize("response", [None, {}, "not a list", 4])
def test_non_list_response_is_invalid(response):
    result = validate_ingestion(response, previous_count=3)

    assert result.status == "invalid"
    assert result.records == []
    assert result.preserve_existing_cases is True
    assert "must be a list" in result.message


def test_mixed_valid_and_malformed_rows_are_partial_and_only_valid_rows_continue():
    valid = {"sample_id": "S-1", "parameter": "Ecoil"}
    result = validate_ingestion(
        [valid, None, [], {"sample_id": "S-2"}],
        required_fields=["sample_id", "parameter"],
    )

    assert result.status == "partial"
    assert result.records == [valid]
    assert result.current_count == 4
    assert result.accepted_count == 1
    assert result.invalid_count == 3
    assert result.invalid_record_indices == [1, 2, 3]
    assert result.preserve_existing_cases is True


def test_all_malformed_rows_are_invalid():
    result = validate_ingestion([None, {}, {"sample_id": ""}], required_fields=["sample_id"])

    assert result.status == "invalid"
    assert result.records == []
    assert result.invalid_count == 3
    assert result.invalid_record_indices == [0, 1, 2]
    assert "No records passed validation" in result.message


@pytest.mark.parametrize(
    "record",
    [
        {"value": math.nan},
        {"value": math.inf},
        {"value": object()},
    ],
)
def test_non_json_or_non_finite_record_is_invalid(record):
    result = validate_ingestion([record])

    assert result.status == "invalid"
    assert result.invalid_record_indices == [0]


def test_required_fields_reject_missing_null_and_blank_but_not_zero():
    records = [
        {"sample_id": "S-1", "value": 0},
        {"sample_id": "S-2", "value": None},
        {"sample_id": "S-3", "value": "  "},
        {"value": 4},
    ]
    result = validate_ingestion(records, required_fields=["sample_id", "value"])

    assert result.status == "partial"
    assert result.records == [records[0]]
    assert result.invalid_record_indices == [1, 2, 3]


@pytest.mark.parametrize("previous_count", [-1, True, 1.5, "5"])
def test_invalid_previous_count_is_invalid(previous_count):
    result = validate_ingestion([{"record_id": 1}], previous_count=previous_count)

    assert result.status == "invalid"
    assert "non-negative integer" in result.message


@pytest.mark.parametrize("required_fields", ["sample_id", ["", "value"], [1]])
def test_invalid_required_fields_argument_is_invalid(required_fields):
    result = validate_ingestion([{"record_id": 1}], required_fields=required_fields)

    assert result.status == "invalid"
    assert "required_fields" in result.message


def test_input_records_are_not_mutated():
    original = [{"record_id": 1}]
    validate_ingestion(original)

    assert original == [{"record_id": 1}]


def test_orchestrator_fetches_generic_client_and_exposes_ok_records():
    records = [{"sample_id": "S-1", "parameter": "Ecoil"}]
    client = FakeGenericClient(FakeFetchResult(records, pages_fetched=2))

    result = orchestrate_ingestion(
        client,
        fetch_method="fetch_records",
        fetch_kwargs={"params": {"state": 31}},
        required_fields=["sample_id", "parameter"],
    )

    assert client.call_kwargs == {"params": {"state": 31}}
    assert result.status == "ok"
    assert result.records == records
    assert result.pages_fetched == 2
    assert result.preserve_existing_cases is False
    assert result.cases_may_be_resolved is False


def test_orchestrator_supports_portal_clients_with_different_fetch_arguments():
    client = FakePortalClient(FakeFetchResult([{"sample_id": "S-2"}]))
    fetch_kwargs = {
        "parameter": "Nitrate",
        "financial_year": "2026-2027",
        "state_id": 27,
    }

    result = orchestrate_ingestion(
        client, fetch_method="fetch_samples", fetch_kwargs=fetch_kwargs
    )

    assert client.call_kwargs == fetch_kwargs
    assert result.status == "ok"
    assert result.records == [{"sample_id": "S-2"}]


def test_orchestrator_client_partial_never_returns_ok_or_exposes_records():
    client = FakeGenericClient(
        FakeFetchResult([{"sample_id": "S-1"}], partial=True)
    )

    result = orchestrate_ingestion(client, fetch_method="fetch_records")

    assert result.status == "partial"
    assert result.records == []
    assert result.client_partial is True
    assert result.preserve_existing_cases is True
    assert result.cases_may_be_resolved is False


def test_orchestrator_empty_result_is_partial_and_preserves_cases():
    client = FakeGenericClient(FakeFetchResult([], pages_fetched=1))

    result = orchestrate_ingestion(
        client, fetch_method="fetch_records", previous_count=12
    )

    assert result.status == "partial"
    assert result.records == []
    assert result.previous_count == 12
    assert result.drop_fraction == 1.0
    assert result.preserve_existing_cases is True


def test_orchestrator_malformed_records_are_invalid_and_not_exposed():
    client = FakePortalClient(FakeFetchResult([None, {}]))

    result = orchestrate_ingestion(client, fetch_method="fetch_samples")

    assert result.status == "invalid"
    assert result.records == []
    assert result.invalid_count == 2
    assert result.preserve_existing_cases is True
    assert result.cases_may_be_resolved is False


def test_orchestrator_suspicious_count_drop_is_partial_and_not_exposed():
    client = FakeGenericClient(
        FakeFetchResult([{"sample_id": str(index)} for index in range(4)])
    )

    result = orchestrate_ingestion(
        client, fetch_method="fetch_records", previous_count=10
    )

    assert result.status == "partial"
    assert result.records == []
    assert result.drop_fraction == 0.6
    assert result.preserve_existing_cases is True


def test_orchestrator_fetch_exception_is_observable_invalid_result():
    client = FakeGenericClient(error=TimeoutError("portal timed out"))

    result = orchestrate_ingestion(client, fetch_method="fetch_records")

    assert result.status == "invalid"
    assert result.records == []
    assert "TimeoutError" in result.message
    assert "portal timed out" in result.warnings[0]
    assert result.preserve_existing_cases is True
    assert result.cases_may_be_resolved is False


def test_orchestrator_client_warnings_make_result_partial():
    client = FakeGenericClient(
        FakeFetchResult(
            [{"sample_id": "S-1"}], warnings=["Page safety limit reached."]
        )
    )

    result = orchestrate_ingestion(client, fetch_method="fetch_records")

    assert result.status == "partial"
    assert result.records == []
    assert "Page safety limit reached." in result.warnings


def test_orchestrator_rejects_unsupported_fetch_method():
    result = orchestrate_ingestion(object(), fetch_method="delete_cases")

    assert result.status == "invalid"
    assert result.records == []
    assert result.preserve_existing_cases is True


@pytest.mark.parametrize(
    "failing_attribute", ["records", "pages_fetched", "partial", "warnings"]
)
def test_orchestrator_converts_result_property_errors_to_invalid(failing_attribute):
    client = FakePortalClient(RaisingFetchResult(failing_attribute))

    result = orchestrate_ingestion(client, fetch_method="fetch_samples")

    assert result.status == "invalid"
    assert result.records == []
    assert failing_attribute in result.message
    assert result.preserve_existing_cases is True
    assert result.cases_may_be_resolved is False


def test_orchestrator_rejects_records_with_zero_fetched_pages():
    client = FakeGenericClient(
        FakeFetchResult([{"sample_id": "S-1"}], pages_fetched=0)
    )

    result = orchestrate_ingestion(client, fetch_method="fetch_records")

    assert result.status == "invalid"
    assert result.records == []
    assert result.preserve_existing_cases is True
    assert result.cases_may_be_resolved is False