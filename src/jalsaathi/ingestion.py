
import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    records: List[Dict[str, Any]]
    status: str
    message: str
    previous_count: Optional[int] = None
    current_count: Optional[int] = None
    accepted_count: int = 0
    invalid_count: int = 0
    invalid_record_indices: List[int] = field(default_factory=list)
    drop_fraction: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    preserve_existing_cases: bool = True
    cases_may_be_resolved: bool = False
    pages_fetched: int = 0
    client_partial: bool = False


def validate_ingestion(
    records: Any,
    previous_count: Optional[int] = None,
    *,
    required_fields: Optional[List[str]] = None,
) -> IngestionResult:
    """
    Validate a fetched batch before downstream processing.

    WQMIS reports do not share a fully confirmed row schema, so callers may
    provide the fields required for their specific report. Every row must be
    a non-empty JSON-compatible dictionary. Empty batches and sharp count
    drops are partial, never evidence that an existing case is resolved.
    """
    if previous_count is not None and (
        isinstance(previous_count, bool)
        or not isinstance(previous_count, int)
        or previous_count < 0
    ):
        return IngestionResult(
            records=[],
            status="invalid",
            message="previous_count must be a non-negative integer or None.",
            previous_count=previous_count,
            preserve_existing_cases=True,
        )

    if required_fields is None:
        required_fields = []
    if not isinstance(required_fields, list) or any(
        not isinstance(name, str) or not name for name in required_fields
    ):
        return IngestionResult(
            records=[],
            status="invalid",
            message="required_fields must be a list of non-empty field names.",
            previous_count=previous_count,
            preserve_existing_cases=True,
        )

    if not isinstance(records, list):
        return IngestionResult(
            records=[],
            status="invalid",
            message="Response records must be a list; preserve existing cases.",
            previous_count=previous_count,
            preserve_existing_cases=True,
        )

    current_count = len(records)
    accepted_records: List[Dict[str, Any]] = []
    invalid_record_indices: List[int] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not record:
            invalid_record_indices.append(index)
            continue
        if any(
            field_name not in record
            or record[field_name] is None
            or (isinstance(record[field_name], str) and not record[field_name].strip())
            for field_name in required_fields
        ):
            invalid_record_indices.append(index)
            continue
        try:
            json.dumps(record, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            invalid_record_indices.append(index)
            continue
        if any(
            isinstance(value, float) and not math.isfinite(value)
            for value in record.values()
        ):
            invalid_record_indices.append(index)
            continue
        accepted_records.append(record)

    accepted_count = len(accepted_records)
    invalid_count = len(invalid_record_indices)
    drop_fraction = None
    if previous_count and previous_count > accepted_count:
        drop_fraction = (previous_count - accepted_count) / previous_count

    metadata = {
        "previous_count": previous_count,
        "current_count": current_count,
        "accepted_count": accepted_count,
        "invalid_count": invalid_count,
        "invalid_record_indices": invalid_record_indices,
        "drop_fraction": drop_fraction,
    }

    if current_count == 0:
        message = "Received an empty batch; preserve existing cases and investigate the data source."
        if previous_count and previous_count > 0:
            message = (
                "Received zero records despite a nonzero previous count; "
                "preserve existing cases and investigate the data source."
            )
        return IngestionResult(
            records=[],
            status="partial",
            message=message,
            **metadata,
            warnings=[message],
            preserve_existing_cases=True,
        )

    if accepted_count == 0:
        message = (
            "No records passed validation; preserve existing cases and investigate the response."
        )
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            **metadata,
            warnings=[message],
            preserve_existing_cases=True,
        )

    warnings: List[str] = []
    if invalid_count:
        warnings.append(
            f"Excluded {invalid_count} malformed record(s) at indexes "
            f"{invalid_record_indices}."
        )

    sharp_drop = bool(
        previous_count
        and previous_count > 0
        and (accepted_count == 0 or accepted_count < previous_count / 2)
    )
    if sharp_drop:
        warnings.append(
            f"Record count dropped from {previous_count} to {accepted_count} "
            "(more than 50%); preserve existing cases and investigate."
        )

    if warnings:
        message = "Partial ingestion: " + " ".join(warnings)
        return IngestionResult(
            records=accepted_records,
            status="partial",
            message=message,
            **metadata,
            warnings=warnings,
            preserve_existing_cases=True,
        )

    return IngestionResult(
        records=accepted_records,
        status="ok",
        message="All records passed ingestion checks.",
        **metadata,
        preserve_existing_cases=False,
    )


def orchestrate_ingestion(
    client: Any,
    *,
    fetch_method: str,
    fetch_kwargs: Optional[Mapping[str, Any]] = None,
    previous_count: Optional[int] = None,
    required_fields: Optional[List[str]] = None,
) -> IngestionResult:
    """Fetch with an existing WQMIS client, then validate before processing.

    ``fetch_method`` is one of the existing client methods:
    ``fetch_records``, ``fetch_villages`` or ``fetch_samples``. Callers pass
    that method's own keyword arguments in ``fetch_kwargs``; no endpoint,
    report schema, or persisted previous count is assumed here.

    ``records`` is populated for normal downstream processing only when the
    final status is ``ok``. Partial and invalid outcomes retain metadata and
    warnings but cannot authorize case deletion or resolution.
    """
    supported_methods = {"fetch_records", "fetch_villages", "fetch_samples"}
    if fetch_method not in supported_methods:
        message = f"Unsupported WQMIS fetch method: {fetch_method!r}."
        logger.error(message)
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            previous_count=previous_count,
            warnings=[message],
            preserve_existing_cases=True,
        )

    if fetch_kwargs is None:
        fetch_kwargs = {}
    if not isinstance(fetch_kwargs, Mapping):
        message = "fetch_kwargs must be a mapping of method arguments."
        logger.error(message)
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            previous_count=previous_count,
            warnings=[message],
            preserve_existing_cases=True,
        )

    fetch = getattr(client, fetch_method, None)
    if not callable(fetch):
        message = f"WQMIS client does not provide callable {fetch_method}."
        logger.error(message)
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            previous_count=previous_count,
            warnings=[message],
            preserve_existing_cases=True,
        )

    call_kwargs = dict(fetch_kwargs)
    if fetch_method == "fetch_records" and previous_count is not None:
        call_kwargs.setdefault("previous_count", previous_count)
    try:
        fetched = fetch(**call_kwargs)
    except Exception as exc:
        message = f"WQMIS fetch failed: {type(exc).__name__}: {exc}"
        logger.exception("WQMIS ingestion fetch failed")
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            previous_count=previous_count,
            warnings=[message],
            preserve_existing_cases=True,
        )

    try:
        fetched_records = getattr(fetched, "records", None)
        pages_fetched = getattr(fetched, "pages_fetched", None)
        client_partial = getattr(fetched, "partial", None)
        fetch_warnings = getattr(fetched, "warnings", None)
    except Exception as exc:
        message = f"WQMIS fetch result could not be read: {type(exc).__name__}: {exc}"
        logger.exception("WQMIS ingestion result inspection failed")
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            previous_count=previous_count,
            warnings=[message],
            preserve_existing_cases=True,
            cases_may_be_resolved=False,
        )

    if (
        not isinstance(pages_fetched, int)
        or isinstance(pages_fetched, bool)
        or pages_fetched < 1
        or not isinstance(client_partial, bool)
        or not isinstance(fetch_warnings, list)
        or any(not isinstance(warning, str) for warning in fetch_warnings)
    ):
        message = "WQMIS client returned an unsupported fetch-result shape."
        logger.error(message)
        return IngestionResult(
            records=[],
            status="invalid",
            message=message,
            previous_count=previous_count,
            warnings=[message],
            preserve_existing_cases=True,
        )

    result = validate_ingestion(
        fetched_records,
        previous_count=previous_count,
        required_fields=required_fields,
    )
    result.pages_fetched = pages_fetched
    result.client_partial = client_partial
    result.warnings = [*fetch_warnings, *result.warnings]

    if client_partial and result.status == "ok":
        result.status = "partial"
        result.message = "WQMIS client marked the fetch partial; preserve existing cases."
        result.warnings.append(result.message)
    elif fetch_warnings and result.status == "ok":
        result.status = "partial"
        result.message = "WQMIS client returned warnings; preserve existing cases."
        result.warnings.append(result.message)

    if result.status != "ok":
        result.records = []
        result.preserve_existing_cases = True
        result.cases_may_be_resolved = False
        logger.warning(
            "WQMIS ingestion did not pass: status=%s pages=%s warnings=%s",
            result.status,
            result.pages_fetched,
            result.warnings,
        )
    else:
        logger.info(
            "WQMIS ingestion passed: records=%s pages=%s",
            result.accepted_count,
            result.pages_fetched,
        )
    return result