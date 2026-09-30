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
