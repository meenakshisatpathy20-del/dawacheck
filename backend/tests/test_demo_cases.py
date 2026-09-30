"""The one-tap demo cases on the home screen (frontend/src/farmer/Home.jsx) must keep their verdicts."""
import json

import pytest

CASES = [
    ({"qr_payload": "DC-QR-1012|EM25-777|0001", "crop": "cotton", "pest": "bollworm"}, "green", None),
    ({"fields": json.dumps({"brand": "Blastguard 75"}), "crop": "cotton", "pest": "jassid"}, "yellow", "R5"),
    ({"fields": json.dumps({"brand": "Tricy Plus"}), "crop": "basmati", "pest": "blast", "state": "punjab"}, "red", "R7"),
    ({"qr_payload": "DC-QR-1007|PF24-117|0001", "crop": "cotton", "pest": "bollworm"}, "red", "R8"),
]


@pytest.mark.parametrize("form,colour,rule", CASES)
def test_home_demo_case(client, form, colour, rule):
    r = client.post("/scan", data={"state": "maharashtra", "lang": "en", **form}).json()
    assert r["status"] == "ok" and r["verdict"] == colour
    if rule:
        assert rule in [f.get("rule") or f.get("id") for f in r["fired"]]


CONFIDOR = """Bayer
CONFIDOR
Imidacloprid 17.8% SL
Systemic Insecticide
Batch No: BCI2407
Mfg. Date: 06/2024  Exp. Date: 05/2099
Net Contents 250 ml"""


def test_real_brand_not_in_catalogue_is_checked_by_formulation(client):
    """A real pack whose brand we do not list still gets crop, dose, PHI and safety checks."""
    r = client.post("/scan", data={"ocr_text": CONFIDOR, "crop": "cotton", "pest": "jassid",
                                   "state": "maharashtra", "area_acre": "1"}).json()
    assert r["verdict"] == "green" and r["product"] is None
    assert [f["id"] for f in r["fired"]] == ["G1"] and "not in our catalogue" in r["fired"][0]["message"]
    assert r["identified"]["formulation"] == "imidacloprid 17.8 SL" and not r["identified"]["needs_confirmation"]
    assert r["dose"] and r["phi"]["days"] and r["safety"]["first_aid"] is not None
    assert all(c["active_ingredient"] == "imidacloprid" for c in r["candidates"])


def test_real_brand_wrong_crop_and_unregistered_strength(client):
    r = client.post("/scan", data={"ocr_text": CONFIDOR, "crop": "tomato", "pest": "jassid"}).json()
    assert r["verdict"] == "yellow"
    r = client.post("/scan", data={"ocr_text": CONFIDOR.replace("17.8% SL", "45% SL"), "crop": "cotton"}).json()
    assert r["verdict"] == "red" and "R1" in [f["id"] for f in r["fired"]]
