"""End-to-end API tests covering every endpoint and the demo script flows."""
import json


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["products"] >= 30 and r["label_claims"] >= 50


def test_scan_by_qr_green_with_dose_and_phi(client):
    r = client.post("/scan", data={"qr_payload": "DC-QR-1002|RK25-001|0007", "crop": "kapas", "pest": "hara tela",
                                   "area_acre": "1", "lang": "hi", "district": "Yavatmal"}).json()
    assert r["verdict"] == "green", r["fired"]
    assert r["product"]["brand"] == "Rakshak Imidaclo"
    assert r["dose"]["mode"] == "tank" and "टंकी" in r["dose"]["text"]
    assert r["phi"]["days"] == 40 and r["safety"]["poison_helpline"] == "1800 116 117"
    assert r["tts_locale"] == "hi-IN"


def test_scan_by_ocr_text_regex_path(client):
    text = "BLASTGUARD 75\nTricyclazole 75% WP\nReg. No: CIR-DEMO-1021\nBatch No: BG25-221\nExpiry: 03/2027"
    r = client.post("/scan", data={"ocr_text": text, "crop": "cotton", "pest": "bollworm"}).json()
    assert r["product"]["brand"] == "Blastguard 75"
    assert r["verdict"] == "yellow" and [f["id"] for f in r["fired"]] == ["R5"]
    assert r["suggestions"], "should list cotton-approved options"


def test_scan_reg_no_mismatch_is_red(client, pid):
    r = client.post("/scan", data={"product_id": pid("Kavach Imida 17.8"),
                                   "fields": json.dumps({"reg_no": "CIR-FAKE-9"}), "crop": "cotton"}).json()
    assert r["verdict"] == "red" and r["fired"][0]["params"]["reason"] == "reg_no"


def test_scan_expired(client, pid):
    r = client.post("/scan", data={"product_id": pid("Manco 75"), "fields": json.dumps({"exp_date": "01/2024"}),
                                   "crop": "tomato", "pest": "early blight"}).json()
    assert r["verdict"] == "red" and "R3" in [f["id"] for f in r["fired"]]


def test_scan_unknown_chemical(client):
    r = client.post("/scan", data={"ocr_text": "SUPERKILL\nZorbafos 30% EC\nBatch: Z1", "crop": "cotton"}).json()
    assert r["verdict"] in ("red", "grey")


def test_scan_needs_input(client):
    assert client.post("/scan", data={}).status_code == 400


def test_basmati_punjab_ban_and_suggestions_exclude_banned(client, pid):
    r = client.post("/scan", data={"product_id": pid("Tricy Plus"), "crop": "basmati", "pest": "blast",
                                   "state": "Punjab"}).json()
    assert r["verdict"] == "red" and "R7" in [f["id"] for f in r["fired"]]
    assert r["export_flags"] and r["export_flags"][0]["market"] == "EU"
    banned = {"carbendazim", "tricyclazole", "propiconazole", "tebuconazole"}
    assert r["suggestions"] and not banned & {s["active_ingredient"] for s in r["suggestions"]}


def test_batch_anomaly_from_seeded_signals(client, pid):
    r = client.post("/scan", data={"product_id": pid("Profex 50"), "fields": json.dumps({"batch": "PF24-117"}),
                                   "crop": "cotton", "pest": "bollworm"}).json()
    assert r["verdict"] == "red" and "R8" in [f["id"] for f in r["fired"]]
    assert all("fake" not in f["message"].lower() for f in r["fired"])


def test_live_date_conflict_creates_signal(client, pid):
    base = {"product_id": pid("Emacure"), "crop": "cotton", "pest": "bollworm", "district": "Wardha"}
    client.post("/scan", data={**base, "fields": json.dumps({"batch": "LIVE-1", "exp_date": "2027-04"})})
    r = client.post("/scan", data={**base, "fields": json.dumps({"batch": "LIVE-1", "exp_date": "2027-09"})}).json()
    assert "R8" in [f["id"] for f in r["fired"]]


def test_bill_scan_flags_and_saving(client):
    items = [{"product_name": "Kavach Imida", "pack_size": "250 ml", "quantity": 2, "price": 1440},
             {"product_name": "Blastguard 75", "pack_size": "120 g", "quantity": 1, "price": 290}]
    r = client.post("/bill", data={"items": json.dumps(items), "crop": "cotton", "pest": "jassid"}).json()
    assert r["not_ok"] == 1 and r["total"] == 1730
    assert r["items"][0]["cheaper"]["brand"] == "Rakshak Imidaclo" and r["saving"] > 0
    assert r["items"][1]["verdict"] == "yellow"


def test_bill_from_ocr_text(client):
    text = "Krishi Kendra\nKavach Imida 17.8 250 ml x2 1440\nTotal 1440"
    r = client.post("/bill", data={"ocr_text": text, "crop": "cotton"}).json()
    assert r["items"][0]["product"]["brand"] == "Kavach Imida 17.8"


def test_mix_check(client, pid):
    r = client.post("/mix-check", json={"product_ids": [pid("Chlorokill 20"), pid("Pyrikill")], "lang": "mr"}).json()
    assert r["verdict"] == "yellow" and "R9" in [f["id"] for f in r["fired"]]
    assert r["remove"][0]["label"] == "Pyrikill" and "reactions" in r["limit_note"]
    assert client.post("/mix-check", json={"product_ids": [1]}).status_code == 422


def test_claims_and_dose(client, pid):
    r = client.get("/claims", params={"product": pid("Spino 45"), "crop": "tomato"}).json()
    assert r["claims"][0]["pest"] == "fruit borer"
    d = client.post("/dose", json={"product_id": pid("Spino 45"), "crop": "tomato", "pest": "fruit borer",
                                   "area_acre": 2, "tank_l": 16}).json()
    assert d["dose"]["tanks"] == 26 and d["dose"]["unit"] == "ml"
    bad = client.post("/dose", json={"product_id": pid("Spino 45"), "crop": "cotton", "area_acre": 1})
    assert bad.status_code == 422


def test_spray_log_passport_rotation(client, pid):
    plot = "GURPREET-PLOT-1"
    s1 = client.post("/spray-log", json={"plot_id": plot, "crop": "basmati", "state": "punjab", "pest": "brown plant hopper",
                                         "product_id": pid("Pymet 50"), "spray_date": "2026-09-01"}).json()
    assert s1["verdict"] == "green" and s1["safe_harvest_date"] == "2026-09-15"
    s2 = client.post("/spray-log", json={"plot_id": plot, "crop": "basmati", "state": "punjab", "pest": "brown plant hopper",
                                         "product_id": pid("Thiamo 25"), "spray_date": "2026-09-20",
                                         "planned_harvest": "2026-09-25"}).json()
    assert s2["verdict"] == "red" and {"R7", "R12"} <= {f["id"] for f in s2["fired"]}
    p = client.get(f"/passport/{plot}").json()
    assert p["safe_harvest_date"] == "2026-10-04" and p["residue_risk"] == "high"
    assert "not a lab certificate" in p["note"]
    rot = client.get("/rotation", params={"plot_id": plot}).json()
    assert rot["status"] == "ok"  # 9B then 4A: different groups
    client.post("/spray-log", json={"plot_id": plot, "crop": "basmati", "state": "punjab",
                                    "product_id": pid("Kavach Imida 17.8"), "spray_date": "2026-09-25"})
    rot = client.get("/rotation", params={"plot_id": plot, "pest": "brown plant hopper"}).json()
    assert rot["status"] == "change" and rot["group"] == "4A"
    assert all(o["moa_group"] != "4A" for o in rot["options"])
    assert all(o["active_ingredient"] != "buprofezin" for o in rot["options"])  # banned for basmati in Punjab
    assert client.get("/passport/NOPE").status_code == 404


def test_sos_and_doctor_card(client, pid):
    client.post("/spray-log", json={"plot_id": "R1", "crop": "cotton", "product_id": pid("Profex 50"),
                                    "spray_date": "2026-09-28", "user_id": "ramesh"})
    r = client.get("/sos", params={"user_id": "ramesh", "lang": "mr"}).json()
    assert r["helplines"][0]["phone"] == "1800 116 117"
    card = r["doctor_card"][0]
    assert card["active_ingredient"] == "profenofos" and card["chem_class"] == "Organophosphate"
    assert "doctor" in card["antidote_from_label"].lower() and card["last_spray"] == "2026-09-28"


def test_weather_demo_and_offline(client):
    r = client.get("/weather-window", params={"demo": "rain", "lang": "hi"}).json()
    assert r["verdict"] == "yellow" and r["source"] == "simulated" and "16:00" in r["text"]
    assert client.get("/weather-window", params={"lat": 20.4, "lon": 78.1}).json()["status"] == "unavailable"


def test_report_radar_and_batch_detail(client, pid):
    scan = client.post("/scan", data={"product_id": pid("Hexa 5"), "fields": json.dumps({"batch": "HX-1"}),
                                      "district": "Guntur", "lat": "16.3", "lon": "80.4"}).json()
    client.post("/report", data={"scan_id": scan["scan_id"], "reason": "leaking cap"})
    client.post("/report", data={"scan_id": scan["scan_id"], "reason": "wrong colour"})
    radar = client.get("/radar").json()
    assert radar["clusters"] and radar["batches"][0]["score"] >= 1.0
    assert any(b["batch"] == "HX-1" and b["signal_type"] == "farmer_report" for b in radar["batches"])
    assert any(b["signal_type"] == "cloned_qr" for b in radar["batches"])
    d = client.get("/radar/batch", params={"batch": "PF24-117"}).json()
    assert len(d["dates_seen"]) == 2 and d["reports"]


def test_catalogue_endpoints(client):
    assert "basmati" in client.get("/crops").json()
    pack = client.get("/offline-pack").json()
    assert len(pack["products"]) >= 30 and set(pack["i18n"]) == {"en", "hi", "mr", "pa", "te"}
    assert client.get("/i18n/pa").json()["verdict.red"].startswith("ਰੁਕੋ")
    assert client.post("/explain", json={"fired": [{"id": "R5", "message": "Not approved for cotton."}]}).json()["text"]


def test_translations_have_every_key():
    from app import i18n
    en = {k for k in i18n.table("en") if not k.startswith("_")}
    for lang in ("hi", "mr", "pa", "te"):
        assert en - set(i18n.table(lang)) == set(), lang
