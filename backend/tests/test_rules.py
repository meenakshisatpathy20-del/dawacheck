"""Unit tests for every rule R1-R13 on hand-built facts (no database)."""
from datetime import date

import pytest

from app.rules import evaluate, load_rules

TODAY = date(2026, 10, 1)


def ids(res):
    return [r["id"] for r in res["fired"]]


def scan_facts(**kw):
    base = {
        "today": TODAY,
        "identified": {"attempted": True, "ai_known": True, "formulation_registered": True, "product_matched": True},
        "ai": {"name": "imidacloprid", "banned": False, "restricted": False},
        "formulation_label": "imidacloprid 17.8 SL",
        "exp_date": date(2028, 1, 1), "crop": "cotton", "claim_crop": "cotton", "pest": "jassid", "state": None,
        "claims": [{"crop": "cotton", "pest": "jassid", "source_file": "major_uses.pdf", "page": 12}],
        "state_bans": [], "batch_signal": None,
    }
    base.update(kw)
    return base


def test_rules_file_is_valid():
    rules = load_rules()
    assert {r["id"] for r in rules} >= {f"R{i}" for i in range(1, 14)}


def test_green_when_everything_matches():
    res = evaluate(scan_facts(), "scan")
    assert res["verdict"] == "green" and res["fired"] == []


def test_r1_unknown_ingredient():
    f = scan_facts(identified={"attempted": True, "ai_known": False, "ai_text": "xyzfos"}, ai=None,
                   formulation_label=None, claims=[])
    res = evaluate(f, "scan")
    assert ids(res) == ["R1"] and res["verdict"] == "red"


def test_r1_unregistered_formulation_and_reg_no_mismatch():
    f = scan_facts(identified={"attempted": True, "ai_known": True, "formulation_registered": False, "product_matched": False})
    assert "R1" in ids(evaluate(f, "scan"))
    f = scan_facts(identified={"attempted": True, "ai_known": True, "formulation_registered": True, "product_matched": True,
                               "reg_no_extracted": "CIR-999", "reg_no_catalogue": "CIR-DEMO-1001"})
    res = evaluate(f, "scan")
    assert ids(res) == ["R1"] and res["fired"][0]["params"]["reason"] == "reg_no"


def test_g1_grey_when_brand_unknown_but_registered():
    f = scan_facts(identified={"attempted": True, "ai_known": True, "formulation_registered": True, "product_matched": False})
    res = evaluate(f, "scan")
    assert ids(res) == ["G1"] and res["verdict"] == "grey"


def test_r2_banned():
    f = scan_facts(ai={"name": "phorate", "banned": True, "restricted": False})
    assert "R2" in ids(evaluate(f, "scan"))


@pytest.mark.parametrize("exp,rule,verdict", [
    (date(2026, 9, 30), "R3", "red"), (date(2026, 10, 20), "R4", "yellow"), (date(2026, 11, 30), None, "green")])
def test_expiry(exp, rule, verdict):
    res = evaluate(scan_facts(exp_date=exp), "scan")
    assert res["verdict"] == verdict
    assert (rule in ids(res)) if rule else not res["fired"]


def test_r5_wrong_crop_cites_source():
    res = evaluate(scan_facts(crop="rice", claim_crop="rice"), "scan")
    assert ids(res) == ["R5"] and res["verdict"] == "yellow"
    assert res["fired"][0]["source"]["file"] == "major_uses.pdf"


def test_r6_wrong_pest_only_when_crop_row_exists():
    res = evaluate(scan_facts(pest="bollworm"), "scan")
    assert ids(res) == ["R6"]


def test_r7_state_ban_respects_effective_date():
    ban = [{"state": "punjab", "crop": "basmati", "effective_from": date(2025, 6, 14), "source_url": "x"}]
    f = scan_facts(crop="basmati", claim_crop="cotton", state="punjab", state_bans=ban)
    assert "R7" in ids(evaluate(f, "scan"))
    f["today"] = date(2025, 6, 1)
    assert "R7" not in ids(evaluate(f, "scan"))


def test_r8_batch_anomaly_threshold():
    assert "R8" in ids(evaluate(scan_facts(batch_signal={"batch": "B1", "score": 1.0, "signal_type": "date_conflict"}), "scan"))
    assert "R8" not in ids(evaluate(scan_facts(batch_signal={"batch": "B1", "score": 0.5}), "scan"))


def mix_item(label, ai, group, colour, form):
    return {"product_id": hash(label), "label": label, "ai_name": ai, "group": group, "scheme": "IRAC",
            "colour": colour, "form_type": form}


def test_mix_rules():
    mixed = [mix_item("A", "chlorpyrifos", "1B", "yellow", "EC"), mix_item("B", "chlorpyrifos", "1B", "yellow", "EC")]
    res = evaluate({"mix": mixed, "today": TODAY}, "mix")
    assert ids(res) == ["R9", "R11"]  # same a.i. is a duplicate, not a group clash
    mixed = [mix_item("A", "imidacloprid", "4A", "blue", "SL"), mix_item("B", "thiamethoxam", "4A", "green", "WG")]
    res = evaluate({"mix": mixed, "today": TODAY}, "mix")
    assert ids(res) == ["R10", "M4"] and res["verdict"] == "yellow"


def test_jar_test_alone_is_info_not_a_warning():
    mixed = [mix_item("A", "mancozeb", "M03", "green", "WP"), mix_item("B", "imidacloprid", "4A", "blue", "SL")]
    res = evaluate({"mix": mixed, "today": TODAY}, "mix")
    assert ids(res) == ["M4"] and res["verdict"] == "green"


def test_rotation_same_group():
    hist = [{"label": "A", "ai_name": "imidacloprid", "group": "4A"}, {"label": "B", "ai_name": "thiamethoxam", "group": "4A"}]
    assert ids(evaluate({"rotation": hist, "today": TODAY}, "rotation")) == ["R10"]
    hist[1]["group"] = "28"
    assert ids(evaluate({"rotation": hist, "today": TODAY}, "rotation")) == []


def test_r12_playbook_example():
    """Spray 1 Oct, 14-day waiting period, harvest planned 10 Oct -> safe from 15 Oct."""
    f = {"today": TODAY, "spray": {"spray_date": date(2026, 10, 1), "phi_days": 14, "planned_harvest": date(2026, 10, 10)}}
    res = evaluate(f, "spray")
    assert ids(res) == ["R12"] and res["fired"][0]["params"]["date"] == "2026-10-15"
    f["spray"]["planned_harvest"] = date(2026, 10, 15)
    assert evaluate(f, "spray")["fired"] == []


def test_r13_weather():
    w = {"hours": [{"time": "14:00", "rain_mm": 0, "rain_prob": 10, "wind_kmh": 5, "temp_c": 30},
                   {"time": "16:00", "rain_mm": 2.0, "rain_prob": 80, "wind_kmh": 5, "temp_c": 28}]}
    res = evaluate({"weather": w, "today": TODAY}, "weather")
    assert ids(res) == ["R13"] and res["fired"][0]["params"]["time"] == "16:00"


def test_worst_colour_wins():
    f = scan_facts(exp_date=date(2026, 10, 10), crop="rice", claim_crop="rice",
                   ai={"name": "x", "banned": True, "restricted": False})
    res = evaluate(f, "scan")
    assert res["verdict"] == "red" and {"R2", "R4", "R5"} <= set(ids(res))
