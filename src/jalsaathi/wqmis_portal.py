"""HTTP integration for the public JJM-WQMIS contaminant reports.

Portal availability is not guaranteed. Callers should retain snapshots and
must treat a partial result as unavailable evidence, not as resolved cases.
"""
from __future__ import annotations

import base64
import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


PORTAL_ROOT = "https://ejalshakti.gov.in/WQMIS/Report"
PORTAL_KEY = b"8080808080808080"
PORTAL_IV = b"8080808080808080"


class WQMISPortalError(RuntimeError):
	"""Raised when the portal response cannot safely be used."""


@dataclass
class PortalFetchResult:
	"""Paginated records and completeness diagnostics for one report."""

	records: list[dict[str, Any]]
	pages_fetched: int
	partial: bool = False
	warnings: list[str] = field(default_factory=list)


@dataclass
class SourceDetails:
	"""Parsed source metadata while retaining the portal's original text."""

	raw_source: Any
	source_type: str | None = None
	scheme_id: str | None = None
	scheme_name: str | None = None
	pws: bool | None = None


@dataclass
class ParameterValue:
	"""Parsed value and unit alongside the exact raw portal value."""

	raw_value: Any
	value: float | None = None
	unit: str | None = None


def encrypt_parameter(value: Any) -> str:
	"""Encrypt one portal parameter using its published AES-CBC settings."""
	plaintext = "" if value is None else str(value)
	ciphertext = AES.new(PORTAL_KEY, AES.MODE_CBC, PORTAL_IV).encrypt(
		pad(plaintext.encode("utf-8"), AES.block_size)
	)
	return base64.b64encode(ciphertext).decode("ascii")


def parse_source_details(raw_source: Any) -> SourceDetails:
	"""Extract known source fields without normalizing away the source text."""
	if not isinstance(raw_source, str):
		return SourceDetails(raw_source=raw_source)

	def capture(pattern: str) -> str | None:
		match = re.search(pattern, raw_source, flags=re.IGNORECASE)
		return match.group(1).strip() if match else None

	source_type = capture(r"Source\s*type\s*:\s*([^\]]+)")
	scheme_id = capture(r"schemeId\s*:\s*([^,\]\s]+)")
	scheme_name = capture(r"scheme\s*name\s*:\s*([^,\]]+)\s*(?=,\s*Type\s*:|\])")
	type_marker = capture(r"(?:,|\[)\s*Type\s*:\s*([^\]]+)")
	pws = type_marker.casefold() == "pws" if type_marker else None
	return SourceDetails(
		raw_source=raw_source,
		source_type=source_type,
		scheme_id=scheme_id,
		scheme_name=scheme_name,
		pws=pws,
	)


def parse_parameter_value(raw_value: Any) -> ParameterValue:
	"""Split a portal value such as ``50.000 (CFU/100 ml)`` defensively."""
	if not isinstance(raw_value, str):
		if isinstance(raw_value, (int, float)) and math.isfinite(float(raw_value)):
			return ParameterValue(raw_value=raw_value, value=float(raw_value))
		return ParameterValue(raw_value=raw_value)

	match = re.fullmatch(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:\((.*?)\))?\s*", raw_value)
	if not match:
		return ParameterValue(raw_value=raw_value)
	value = float(match.group(1))
	if not math.isfinite(value):
		return ParameterValue(raw_value=raw_value)
	unit = match.group(2).strip() if match.group(2) else None
	return ParameterValue(raw_value=raw_value, value=value, unit=unit or None)


def parse_sample_record(record: Mapping[str, Any]) -> dict[str, Any]:
	"""Add parsed fields while leaving all original portal fields intact."""
	parsed = dict(record)
	raw_source = record.get("sample_sourceName")
	source = parse_source_details(raw_source)
	parsed.update(
		{
			"raw_source": raw_source,
			"source_type": source.source_type,
			"scheme_id": source.scheme_id,
			"scheme_name": source.scheme_name,
			"pws": source.pws,
		}
	)
	raw_value = record.get("Parametervalue")
	parameter_value = parse_parameter_value(raw_value)
	parsed.update(
		{
			"raw_value": raw_value,
			"value": parameter_value.value,
			"unit": parameter_value.unit,
		}
	)
	return parsed


class WQMISPortalClient:
	"""Session-aware client for WQMIS's encrypted report endpoints.

	``last_good_counts`` may be a persisted mutable mapping keyed by
	``"<state-id>:<parameter>"``. A suspicious run is marked partial and does
	not overwrite its prior count.
	"""

	def __init__(
		self,
		*,
		root_url: str = PORTAL_ROOT,
		timeout: float = 30.0,
		max_retries: int = 2,
		backoff_seconds: float = 0.5,
		request_pause_seconds: float = 0.25,
		session: requests.Session | None = None,
		sleep: Callable[[float], None] = time.sleep,
		last_good_counts: dict[str, int] | None = None,
	) -> None:
		if max_retries < 0:
			raise ValueError("max_retries cannot be negative")
		if timeout <= 0:
			raise ValueError("timeout must be positive")
		self.root_url = root_url.rstrip("/")
		self.timeout = timeout
		self.max_retries = max_retries
		self.backoff_seconds = backoff_seconds
		self.request_pause_seconds = request_pause_seconds
		self.session = session or requests.Session()
		self.sleep = sleep
		self.last_good_counts = last_good_counts if last_good_counts is not None else {}
		self._session_initialized = False

	@staticmethod
	def encrypted_params(params: Mapping[str, Any]) -> dict[str, str]:
		"""Return portal parameter names with every value AES-encrypted."""
		return {name: encrypt_parameter(value) for name, value in params.items()}

	@staticmethod
	def _filters(
		parameter: str,
		financial_year: str,
		state_id: Any = "",
		district_id: Any = "",
		block_id: Any = "",
		panchayat_id: Any = "",
		village_id: Any = "",
	) -> dict[str, Any]:
		return {
			"paraname": parameter,
			"fy": financial_year,
			"stid": state_id,
			"dtid": district_id,
			"blid": block_id,
			"gpid": panchayat_id,
			"villid": village_id,
		}

	def initialize_session(
		self,
		*,
		parameter: str,
		financial_year: str,
		state_id: Any = "",
		district_id: Any = "",
		block_id: Any = "",
		panchayat_id: Any = "",
		village_id: Any = "",
	) -> None:
		"""Open the sample-list page to obtain the portal session cookie."""
		if self._session_initialized:
			return
		url = f"{self.root_url}/Contaminantwisesamplelist"
		self._request(
			"GET",
			url,
			params=self._filters(
				parameter,
				financial_year,
				state_id,
				district_id,
				block_id,
				panchayat_id,
				village_id,
			),
			expect_json=False,
		)
		self._session_initialized = True

	def _request(
		self,
		method: str,
		url: str,
		*,
		params: Mapping[str, Any],
		expect_json: bool = True,
	) -> Any:
		encrypted = self.encrypted_params(params)
		last_error: Exception | None = None
		for attempt in range(self.max_retries + 1):
			try:
				response = self.session.request(
					method,
					url,
					params=encrypted if method == "GET" else None,
					data=encrypted if method == "POST" else None,
					timeout=self.timeout,
				)
				status = response.status_code
				if status >= 400:
					error = requests.HTTPError(f"WQMIS returned HTTP {status}")
					if status != 429 and not 500 <= status <= 599:
						raise WQMISPortalError(str(error)) from error
					last_error = error
				elif not expect_json:
					return response
				else:
					text = response.text
					if not text or not text.strip():
						return []
					try:
						return response.json()
					except (ValueError, json.JSONDecodeError) as exc:
						raise WQMISPortalError("WQMIS returned malformed JSON") from exc
			except WQMISPortalError:
				raise
			except requests.RequestException as exc:
				last_error = exc

			if attempt < self.max_retries:
				self.sleep(self.backoff_seconds * (2**attempt))

		raise WQMISPortalError(
			f"WQMIS {method} request failed after {self.max_retries + 1} attempts"
		) from last_error

	@staticmethod
	def extract_records(payload: Any) -> list[dict[str, Any]]:
		"""Extract Contaminantwise rows, accepting common wrapper variants."""
		if payload is None or payload == "":
			return []
		if isinstance(payload, list):
			rows = payload
		elif isinstance(payload, dict):
			rows = payload.get("Contaminantwise")
			if rows is None:
				rows = payload.get("data", payload.get("records", []))
			if rows is None:
				return []
		else:
			raise WQMISPortalError("WQMIS response root must be an object or list")
		if not isinstance(rows, list):
			raise WQMISPortalError("WQMIS Contaminantwise field must be a list")
		if any(not isinstance(row, dict) for row in rows):
			raise WQMISPortalError("WQMIS Contaminantwise rows must be objects")
		return rows

	def _fetch_pages(
		self,
		endpoint: str,
		params: Mapping[str, Any],
		*,
		method: str = "POST",
		max_pages: int = 1000,
	) -> PortalFetchResult:
		if max_pages < 1:
			raise ValueError("max_pages must be at least 1")
		records: list[dict[str, Any]] = []
		page = 1
		pages_fetched = 0
		while pages_fetched < max_pages:
			page_params = {**params, "cpage": page}
			payload = self._request(
				method,
				f"{self.root_url}/{endpoint.lstrip('/')}" ,
				params=page_params,
			)
			page_records = self.extract_records(payload)
			pages_fetched += 1
			if not page_records:
				break
			records.extend(page_records)
			page += 1
			if self.request_pause_seconds:
				self.sleep(self.request_pause_seconds)
		else:
			return PortalFetchResult(
				records=records,
				pages_fetched=pages_fetched,
				partial=True,
				warnings=[f"Stopped at safety limit of {max_pages} pages."],
			)
		return PortalFetchResult(records=records, pages_fetched=pages_fetched)

	def _ensure_session(self, filters: Mapping[str, Any]) -> None:
		self.initialize_session(
			parameter=str(filters["paraname"]),
			financial_year=str(filters["fy"]),
			state_id=filters["stid"],
			district_id=filters["dtid"],
			block_id=filters["blid"],
			panchayat_id=filters["gpid"],
			village_id=filters["villid"],
		)

	def fetch_villages(
		self,
		*,
		parameter: str,
		financial_year: str,
		state_id: Any,
		district_id: Any = "",
		block_id: Any = "",
		panchayat_id: Any = "",
		village_id: Any = "",
		max_pages: int = 1000,
	) -> PortalFetchResult:
		"""Fetch failed-village rows and guard sudden state/parameter drops."""
		filters = self._filters(
			parameter,
			financial_year,
			state_id,
			district_id,
			block_id,
			panchayat_id,
			village_id,
		)
		self._ensure_session(filters)
		result = self._fetch_pages(
			"ContaminantwiseVillagefil/",
			{key: filters[key] for key in ("paraname", "stid", "dtid", "blid", "gpid", "villid", "fy")},
			max_pages=max_pages,
		)
		key = f"{state_id}:{parameter}"
		previous = self.last_good_counts.get(key)
		count = len(result.records)
		if previous is not None and previous > 0 and (
			count == 0 or count < previous / 2
		):
			result.partial = True
			result.warnings.append(
				f"Completeness guard: {count} villages after {previous} previously; "
				"keep existing cases unchanged."
			)
		elif not result.partial:
			self.last_good_counts[key] = count
		return result

	def fetch_samples(
		self,
		*,
		parameter: str,
		financial_year: str,
		state_id: Any,
		district_id: Any = "",
		block_id: Any = "",
		village_id: Any = "",
		max_pages: int = 1000,
	) -> PortalFetchResult:
		"""Fetch and enrich sample rows while retaining raw portal values."""
		filters = self._filters(
			parameter,
			financial_year,
			state_id,
			district_id,
			block_id,
			"",
			village_id,
		)
		self._ensure_session(filters)
		result = self._fetch_pages(
			"Contaminantwisesamplefillist/",
			{key: filters[key] for key in ("paraname", "stid", "dtid", "villid", "fy")},
			max_pages=max_pages,
		)
		result.records = [parse_sample_record(row) for row in result.records]
		return result

	def fetch_count_report(
		self,
		*,
		financial_year: str,
		state: Any = "",
		district: Any = "",
		block: Any = "",
		gram_panchayat: Any = "",
		village: Any = "",
		is_pws: Any = "",
		scheme_id: Any = "",
		sample_type: Any = "",
		page: int = 1,
		parameter: str = "Ecoil",
	) -> Any:
		"""Fetch the documented count report; district calls may return HTTP 500."""
		self.initialize_session(parameter=parameter, financial_year=financial_year)
		return self._request(
			"GET",
			f"{self.root_url}/GetContaminantwiseData",
			params={
				"cpage": page,
				"st": state,
				"dt": district,
				"bl": block,
				"gp": gram_panchayat,
				"vill": village,
				"fy": financial_year,
				"IsPws": is_pws,
				"SchemeId": scheme_id,
				"SampleType": sample_type,
			},
		)
