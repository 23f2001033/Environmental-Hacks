"""Small, defensive HTTP client for paginated WQMIS JSON endpoints.

The endpoint URL and pagination parameter names are configurable because the
WQMIS report portal has returned HTTP 500 errors and its exact live endpoint
must be confirmed before production ingestion is enabled.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen


JSON = dict[str, Any] | list[Any]
Transport = Callable[[str, float], bytes]


class WQMISClientError(RuntimeError):
    """Raised when WQMIS cannot return a usable JSON response."""


@dataclass
class FetchResult:
    """Records fetched from WQMIS plus basic completeness diagnostics."""

    records: list[dict[str, Any]]
    pages_fetched: int
    partial: bool = False
    warnings: list[str] = field(default_factory=list)


def _default_transport(url: str, timeout: float) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "JalSaathi/0.1 (WQMIS data client)",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


class WQMISClient:
    """Fetch records from a JSON endpoint with retries and pagination.

    Args:
        endpoint_url: Exact WQMIS JSON endpoint; do not guess this URL.
        page_param: Query parameter used for the page number.
        page_size_param: Query parameter used for requested page size.
        page_size: Requested records per page.
        max_retries: Number of retries after the initial request.
        transport: Optional function ``(url, timeout) -> response_bytes`` for tests.
    """

    def __init__(
        self,
        endpoint_url: str,
        *,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
        page_param: str = "page",
        page_size_param: str = "page_size",
        page_size: int = 100,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must be an http(s) URL")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.page_param = page_param
        self.page_size_param = page_size_param
        self.page_size = page_size
        self.transport = transport or _default_transport
        self.sleep = sleep

    def _url_for_page(self, page: int, params: dict[str, Any] | None) -> str:
        parts = urlsplit(self.endpoint_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.update({str(k): str(v) for k, v in (params or {}).items()})
        query[self.page_param] = str(page)
        query[self.page_size_param] = str(self.page_size)
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    def _request_json(self, url: str) -> JSON:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                raw = self.transport(url, self.timeout)
                try:
                    payload = json.loads(raw.decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise WQMISClientError(
                        f"WQMIS returned invalid JSON for {url}"
                    ) from exc

                if not isinstance(payload, (dict, list)):
                    raise WQMISClientError("WQMIS JSON root must be an object or list")
                return payload

            except HTTPError as exc:
                last_error = exc
                retryable = exc.code == 429 or 500 <= exc.code <= 599
                if not retryable:
                    raise WQMISClientError(
                        f"WQMIS returned non-retryable HTTP {exc.code}"
                    ) from exc
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
            except WQMISClientError:
                raise

            if attempt < self.max_retries:
                self.sleep(self.backoff_seconds * (2**attempt))

        raise WQMISClientError(
            f"WQMIS request failed after {self.max_retries + 1} attempts"
        ) from last_error

    @staticmethod
    def extract_records(payload: JSON) -> list[dict[str, Any]]:
        """Extract record dictionaries from common JSON response shapes."""
        if isinstance(payload, list):
            raw_records = payload
        else:
            raw_records = payload.get("records")
            if raw_records is None:
                raw_records = payload.get("data")
            if raw_records is None:
                # A single record object is accepted; metadata-only objects are not.
                looks_like_record = any(
                    key in payload for key in ("village", "village_id", "parameter")
                )
                raw_records = [payload] if looks_like_record else []

        if not isinstance(raw_records, list):
            raise WQMISClientError("WQMIS records/data field must be a list")

        if any(not isinstance(record, dict) for record in raw_records):
            raise WQMISClientError("WQMIS returned a non-object item in its records")
        return raw_records

    def _has_next_page(self, payload: JSON, page: int, record_count: int) -> bool:
        if isinstance(payload, dict):
            if isinstance(payload.get("has_more"), bool):
                return payload["has_more"]
            if "next_page" in payload:
                return payload["next_page"] is not None and payload["next_page"] is not False
            if "next" in payload:
                return bool(payload["next"])
            total_pages = payload.get("total_pages")
            if isinstance(total_pages, int):
                return page < total_pages
            last_page = payload.get("last_page")
            if isinstance(last_page, int):
                return page < last_page

        # Fallback for simple page-number APIs without pagination metadata.
        return record_count >= self.page_size

    def fetch_records(
        self,
        *,
        params: dict[str, Any] | None = None,
        previous_count: int | None = None,
        max_pages: int = 100,
    ) -> FetchResult:
        """Fetch pages and flag suspiciously incomplete totals.

        A count of zero after previously seeing records, or a drop greater than
        50%, is flagged as partial. Callers must not interpret it as resolution.
        """
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        all_records: list[dict[str, Any]] = []
        warnings: list[str] = []
        page = 1
        pages_fetched = 0

        while pages_fetched < max_pages:
            payload = self._request_json(self._url_for_page(page, params))
            page_records = self.extract_records(payload)
            all_records.extend(page_records)
            pages_fetched += 1

            if not self._has_next_page(payload, page, len(page_records)):
                break

            if isinstance(payload, dict) and isinstance(payload.get("next_page"), int):
                page = payload["next_page"]
            else:
                page += 1
        else:
            warnings.append(f"Stopped at safety limit of {max_pages} pages.")

        partial = False
        if previous_count is not None and previous_count > 0:
            if not all_records:
                partial = True
                warnings.append(
                    "Completeness guard: fetched 0 records after a non-empty prior run."
                )
            elif len(all_records) < previous_count * 0.5:
                partial = True
                warnings.append(
                    "Completeness guard: fetched less than 50% of the previous record count."
                )

        return FetchResult(
            records=all_records,
            pages_fetched=pages_fetched,
            partial=partial,
            warnings=warnings,
        )
