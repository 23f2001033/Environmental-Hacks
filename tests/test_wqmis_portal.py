import base64
import json

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from jalsaathi.wqmis_portal import (
    PORTAL_IV,
    PORTAL_KEY,
    WQMISPortalClient,
    WQMISPortalError,
    encrypt_parameter,
    parse_parameter_value,
    parse_sample_record,
    parse_source_details,
)


class FakeResponse:
    def __init__(self, payload=None, *, text=None, status_code=200):
        self.status_code = status_code
        self.text = json.dumps(payload) if text is None else text
        self.payload = payload

    def json(self):
        if self.text == "not-json":
            raise ValueError("invalid JSON")
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def decoded_params(call):
    return {
        key: unpad(
            AES.new(PORTAL_KEY, AES.MODE_CBC, PORTAL_IV).decrypt(
                base64.b64decode(value)
            ),
            AES.block_size,
        ).decode()
        for key, value in call[2]["params" if call[0] == "GET" else "data"].items()
    }


def test_aes_128_cbc_pkcs7_and_base64_round_trip():
    encrypted = encrypt_parameter("Ecoil")
    ciphertext = base64.b64decode(encrypted, validate=True)
    assert len(ciphertext) % AES.block_size == 0
    assert unpad(
        AES.new(PORTAL_KEY, AES.MODE_CBC, PORTAL_IV).decrypt(ciphertext),
        AES.block_size,
    ) == b"Ecoil"


def test_source_parser_preserves_raw_and_extracts_fields():
    raw = (
        "Location : MAHMOOD PUR KEERAT CHHIBRAMAU [ Source type : Deep Tubewell ] "
        "[ schemeId : 20014829, scheme name : MAHMOOD PUR KEERAT GRAMIN PEYJAL YOJNA, Type : PWS ]"
    )
    result = parse_source_details(raw)
    assert result.raw_source == raw
    assert result.source_type == "Deep Tubewell"
    assert result.scheme_id == "20014829"
    assert result.scheme_name == "MAHMOOD PUR KEERAT GRAMIN PEYJAL YOJNA"
    assert result.pws is True
    assert parse_source_details(None).raw_source is None


def test_parameter_value_parser_keeps_raw_and_handles_bad_values():
    result = parse_parameter_value("50.000 (CFU/100 ml)")
    assert result.raw_value == "50.000 (CFU/100 ml)"
    assert result.value == 50.0
    assert result.unit == "CFU/100 ml"
    malformed = parse_parameter_value("unknown")
    assert malformed.raw_value == "unknown"
    assert malformed.value is None
    assert malformed.unit is None


def test_sample_parser_keeps_original_fields_and_adds_parsed_fields():
    raw_source = "[ Source type : Deep Tubewell ] [ schemeId : 8, scheme name : Plan, Type : PWS ]"
    record = {
        "SampleId": "S-1",
        "sample_sourceName": raw_source,
        "Parametervalue": "60.000 (mg/l)",
        "Acceptablelimit": "45",
        "Permissiblelimit": "45",
    }
    parsed = parse_sample_record(record)
    assert parsed["SampleId"] == "S-1"
    assert parsed["Acceptablelimit"] == "45"
    assert parsed["raw_source"] == raw_source
    assert parsed["raw_value"] == "60.000 (mg/l)"
    assert parsed["value"] == 60.0
    assert parsed["unit"] == "mg/l"


def test_initialization_and_village_post_encrypt_documented_parameters_and_paginates():
    session = FakeSession(
        [
            FakeResponse(text="session page"),
            FakeResponse({"Contaminantwise": [{"village": "A"}]}),
            FakeResponse({"Contaminantwise": [{"village": "B"}]}),
            FakeResponse({"Contaminantwise": []}),
        ]
    )
    client = WQMISPortalClient(
        session=session, sleep=lambda _: None, request_pause_seconds=0
    )
    result = client.fetch_villages(
        parameter="Ecoil", financial_year="2026-2027", state_id=31, district_id=481
    )
    assert [row["village"] for row in result.records] == ["A", "B"]
    assert result.pages_fetched == 3
    assert session.calls[0][0:2] == (
        "GET",
        "https://ejalshakti.gov.in/WQMIS/Report/Contaminantwisesamplelist",
    )
    assert decoded_params(session.calls[0]) == {
        "paraname": "Ecoil",
        "fy": "2026-2027",
        "stid": "31",
        "dtid": "481",
        "blid": "",
        "gpid": "",
        "villid": "",
    }
    assert session.calls[1][0] == "POST"
    assert session.calls[1][1].endswith("/ContaminantwiseVillagefil/")
    assert decoded_params(session.calls[1]) == {
        "paraname": "Ecoil",
        "stid": "31",
        "dtid": "481",
        "blid": "",
        "gpid": "",
        "villid": "",
        "fy": "2026-2027",
        "cpage": "1",
    }
    assert decoded_params(session.calls[3])["cpage"] == "3"


def test_sample_post_uses_documented_params_and_empty_body_stops():
    session = FakeSession(
        [
            FakeResponse(text="session"),
            FakeResponse(
                {"Contaminantwise": [{"sample_sourceName": "", "Parametervalue": ""}]}
            ),
            FakeResponse(text=" "),
        ]
    )
    client = WQMISPortalClient(
        session=session, sleep=lambda _: None, request_pause_seconds=0
    )
    result = client.fetch_samples(
        parameter="Nitrate", financial_year="2026-2027", state_id=27
    )
    assert result.pages_fetched == 2
    assert result.records[0]["raw_source"] == ""
    assert result.records[0]["raw_value"] == ""
    assert decoded_params(session.calls[1]) == {
        "paraname": "Nitrate",
        "stid": "27",
        "dtid": "",
        "villid": "",
        "fy": "2026-2027",
        "cpage": "1",
    }


def test_count_report_get_uses_documented_parameter_names():
    session = FakeSession([FakeResponse(text="session"), FakeResponse({"counts": []})])
    client = WQMISPortalClient(session=session, sleep=lambda _: None)
    assert client.fetch_count_report(financial_year="2026-2027", state=31) == {"counts": []}
    call = session.calls[1]
    assert call[0] == "GET"
    assert call[1].endswith("/GetContaminantwiseData")
    assert decoded_params(call) == {
        "cpage": "1",
        "st": "31",
        "dt": "",
        "bl": "",
        "gp": "",
        "vill": "",
        "fy": "2026-2027",
        "IsPws": "",
        "SchemeId": "",
        "SampleType": "",
    }


def test_count_drop_guard_marks_zero_partial_and_preserves_last_good_count():
    counts = {"31:Ecoil": 10}
    session = FakeSession(
        [FakeResponse(text="session"), FakeResponse({"Contaminantwise": []})]
    )
    client = WQMISPortalClient(
        session=session,
        last_good_counts=counts,
        sleep=lambda _: None,
        request_pause_seconds=0,
    )
    result = client.fetch_villages(
        parameter="Ecoil", financial_year="2026-2027", state_id=31
    )
    assert result.partial is True
    assert any("keep existing cases unchanged" in warning for warning in result.warnings)
    assert counts["31:Ecoil"] == 10


def test_count_drop_over_half_is_partial_but_exact_half_is_not():
    def fetch(row_count):
        session = FakeSession(
            [
                FakeResponse(text="session"),
                FakeResponse({"Contaminantwise": [{}] * row_count}),
                FakeResponse({"Contaminantwise": []}),
            ]
        )
        counts = {"31:Ecoil": 10}
        result = WQMISPortalClient(
            session=session,
            last_good_counts=counts,
            sleep=lambda _: None,
            request_pause_seconds=0,
        ).fetch_villages(
            parameter="Ecoil", financial_year="2026-2027", state_id=31
        )
        return result, counts

    partial, partial_counts = fetch(4)
    exact_half, exact_half_counts = fetch(5)
    assert partial.partial is True
    assert partial_counts["31:Ecoil"] == 10
    assert exact_half.partial is False
    assert exact_half_counts["31:Ecoil"] == 5


def test_malformed_json_and_malformed_rows_are_reported():
    session = FakeSession([FakeResponse(text="session"), FakeResponse(text="not-json")])
    client = WQMISPortalClient(session=session, sleep=lambda _: None)
    with pytest.raises(WQMISPortalError, match="malformed JSON"):
        client.fetch_samples(parameter="Ecoil", financial_year="2026-2027", state_id=31)

    with pytest.raises(WQMISPortalError, match="rows must be objects"):
        WQMISPortalClient.extract_records({"Contaminantwise": ["bad-row"]})


def test_retries_server_error_but_does_not_retry_client_error():
    server_error = FakeResponse(text="error", status_code=500)
    session = FakeSession([server_error, FakeResponse(text="session"), FakeResponse({"Contaminantwise": []})])
    client = WQMISPortalClient(
        session=session, max_retries=1, sleep=lambda _: None, request_pause_seconds=0
    )
    result = client.fetch_villages(
        parameter="Ecoil", financial_year="2026-2027", state_id=31
    )
    assert result.records == []
    assert len(session.calls) == 3

    client_error = FakeSession([FakeResponse(text="no", status_code=404)])
    with pytest.raises(WQMISPortalError, match="HTTP 404"):
        WQMISPortalClient(session=client_error, max_retries=3).initialize_session(
            parameter="Ecoil", financial_year="2026-2027"
        )
    assert len(client_error.calls) == 1


def test_page_safety_limit_is_partial():
    session = FakeSession(
        [FakeResponse(text="session"), FakeResponse({"Contaminantwise": [{}]})]
    )
    client = WQMISPortalClient(
        session=session, sleep=lambda _: None, request_pause_seconds=0
    )
    result = client.fetch_samples(
        parameter="Ecoil", financial_year="2026-2027", state_id=31, max_pages=1
    )
    assert result.partial is True
    assert result.pages_fetched == 1