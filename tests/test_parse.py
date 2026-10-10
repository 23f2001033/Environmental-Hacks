from jalsaathi import parse

RAW = ("Location : MAHMOOD PUR KEERAT CHHIBRAMAU  [ Source type : Deep Tubewell ]  "
       "[ schemeId : 20014829, scheme name : MAHMOOD PUR KEERAT GRAMIN PEYJAL YOJNA, Type : PWS ]")


def test_parse_source_real_record():
    out = parse.parse_source(RAW)
    assert out["source_type"] == "Deep Tubewell"
    assert out["scheme_id"] == "20014829"
    assert out["scheme_name"] == "MAHMOOD PUR KEERAT GRAMIN PEYJAL YOJNA"
    assert out["pws"] is True
    assert out["location"] == "MAHMOOD PUR KEERAT CHHIBRAMAU"


def test_parse_source_missing_parts():
    assert parse.parse_source(None)["scheme_id"] is None
    assert parse.parse_source("Location : X [ ]")["source_type"] is None


def test_parse_value_units():
    assert parse.parse_value("50.000 (CFU/100 ml)") == (50.0, "CFU/100 ml")
    assert parse.parse_value("60.000 (mg/l)") == (60.0, "mg/l")
    assert parse.parse_value("1.2") == (1.2, None)
    assert parse.parse_value("Present") == (None, None)
    assert parse.parse_value(None) == (None, None)


def test_parse_approval_ist():
    assert parse.parse_approval("21/08/2026 13:57:00") == "2026-08-21T13:57:00+05:30"
    assert parse.parse_approval("bad") is None


def test_village_key_prefers_id_then_slug():
    assert parse.village_key(31, "Hardoi", "Harpalpur", "BEHTA LAKHI", 412558) == "412558"
    assert parse.village_key(27, "Baran", "Anta", "Dhabla Kalayanpura", None) == "27-baran-anta-dhabla-kalayanpura"


def test_sample_from_portal_combines_rows():
    vrow = {"State": "Uttar Pradesh", "StateId": 31, "District": "Kannauj", "DistrictId": 486, "Block": "Chhibramau",
            "BlockId": 5103, "Grampanchayat": "MAHMOOD PUR KEERAT", "GrampanchayatId": 180533,
            "Village": "Mahmood Pur Keerat", "VillageId": 418795}
    srow = {"sample_sourceName": RAW, "SampleId": "U3027060S38720650", "Acceptablelimit": "0", "Permissiblelimit": "0",
            "Parametervalue": "50.000 (CFU/100 ml)", "labname": "State Level Water Analysis Laboratory ",
            "s_report_approval_action_time": "21/08/2026 13:57:00"}
    s = parse.sample_from_portal(vrow, srow, "Ecoil")
    assert s["value"] == 50.0 and s["unit"] == "CFU/100 ml"
    assert s["acceptable_limit"] == 0.0 and s["scheme_id"] == "20014829"
    assert s["lab"] == "State Level Water Analysis Laboratory"
    assert s["lab_approval"] == "2026-08-21T13:57:00+05:30"
