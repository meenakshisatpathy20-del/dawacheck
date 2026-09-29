from datetime import date

from app.ai import extract, qr
from app.services import dose


def test_dose_per_tank():
    claim = {"dose_form_ha": [300, 400], "unit": "ml", "water_l_ha": 300, "phi_days": 14}
    card = dose.compute(claim, area_acre=1, tank_l=15)
    # 1 acre = 0.4047 ha -> 121 L spray -> 9 tanks; 300 ml/ha * 0.4047 / 9 = 13.5 ml
    assert card["tanks"] == 9 and card["per_tank"] == 13
    assert card["per_tank_range"] == [13, 18]


def test_dose_granules_have_no_tank():
    claim = {"dose_form_ha": [18750, 25000], "unit": "g", "water_l_ha": None}
    card = dose.compute(claim, area_acre=1, form_type="GR")
    assert card["mode"] == "granule" and card["unit"] == "kg" and card["total_range"][0] == 7.59


def test_safe_harvest_date():
    assert dose.safe_harvest_date(date(2026, 10, 1), 14) == date(2026, 10, 15)
    assert dose.safe_harvest_date(date(2026, 10, 1), None) is None


LABEL = """KAVACH IMIDA 17.8
Imidacloprid 17.8% SL
Reg. No.: CIR-DEMO-1001
Batch No: KI25-042
Mfg. Date: 06/2025
Expiry Date: 05/2027
Yellow label
"""


def test_regex_label():
    d, method = extract.extract_label(LABEL, ["imidacloprid", "thiamethoxam"])
    assert method == "regex"
    assert d["active_ingredient"] == "imidacloprid" and d["strength_pct"] == 17.8 and d["formulation"] == "SL"
    assert d["reg_no"] == "CIR-DEMO-1001" and d["batch"] == "KI25-042" and d["toxicity_colour"] == "yellow"
    assert extract.parse_date(d["exp_date"], end_of_month=True) == date(2027, 5, 31)


def test_parse_dates():
    assert extract.parse_date("12/03/2027") == date(2027, 3, 12)  # Indian day-first
    assert extract.parse_date("Mar 2027", end_of_month=True) == date(2027, 3, 31)
    assert extract.parse_date("2027-02", end_of_month=True) == date(2027, 2, 28)
    assert extract.parse_date("garbage") is None


def test_regex_bill():
    text = """Shri Ram Krishi Kendra
Kavach Imida 17.8 250 ml x2 1440
Blastguard 75 120 g 290
Total 1730"""
    b = extract.regex_bill(text)
    assert b["total"] == 1730
    assert b["items"][0]["pack_size"] == "250 ml" and b["items"][0]["quantity"] == 2 and b["items"][0]["price"] == 1440
    assert "Kavach Imida" in b["items"][0]["product_name"]


def test_qr_payload_shapes():
    assert qr.parse_payload("DC-QR-1001|KI25-042|0001")["qr_id"] == "DC-QR-1001"
    u = qr.parse_payload("https://verify.example/p?uid=U1&batch=B7&exp=2027-05")
    assert u["qr_id"] == "U1" and u["batch"] == "B7" and u["exp_date"] == "2027-05"
    kv = qr.parse_payload("Batch No: B9; Mfg: 01/2025; Exp: 12/2026; Reg No: CIR-1")
    assert kv["batch"] == "B9" and kv["reg_no"] == "CIR-1" and kv["mfg_date"] == "01/2025"
    assert qr.parse_payload('{"uid": "X", "lot": "L1"}')["batch"] == "L1"


def test_explain_guard_rejects_new_numbers():
    from app.ai import explain
    assert explain._numbers("spray 30 ml on 15 Oct") == {"30", "15"}
    fired = [{"id": "R5", "message_en": "Not approved for cotton.", "message": "Not approved for cotton."}]
    assert explain.explain(fired)["method"] == "template"  # LLM off in tests
