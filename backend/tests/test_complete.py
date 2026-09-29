"""Tests for the second build pass: Telugu, D1, OCR field crops, admin, submissions,
reminders, job queue, grounded explanation, bilingual Doctor Card."""
import io
import json
import shutil
import time
from datetime import date

import pytest

ADMIN = {"X-Admin-Token": "test-admin-token"}


def label_png(lines: list[str]) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    im = Image.new("RGB", (900, 80 + 60 * len(lines)), "white")
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((40, 40 + 60 * i), ln, fill="black", font=font)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def test_telugu_everywhere(client, pid):
    r = client.post("/scan", data={"product_id": pid("Blastguard 75"), "crop": "cotton", "lang": "te"}).json()
    assert r["tts_locale"] == "te-IN" and "పత్తి" in r["fired"][0]["message"]
    assert client.get("/i18n/te").json()["verdict.red"].startswith("ఆగండి")


def test_d1_data_incomplete_only_for_pack_photos(client, pid):
    text = "KAVACH IMIDA 17.8\nImidacloprid 17.8% SL\nReg. No: CIR-DEMO-1001"
    r = client.post("/scan", data={"ocr_text": text, "crop": "cotton", "pest": "jassid"}).json()
    d1 = next(f for f in r["fired"] if f["id"] == "D1")
    assert r["verdict"] == "yellow" and "expiry date" in d1["message"] and "batch number" in d1["message"]
    picked = client.post("/scan", data={"product_id": pid("Kavach Imida 17.8"), "crop": "cotton", "pest": "jassid"}).json()
    assert picked["verdict"] == "green"


def test_mismatched_strength_asks_to_confirm(client):
    text = "KAVACH IMIDA\nImidacloprid 30.5% SC\nReg. No: CIR-DEMO-1001\nBatch No: X1\nExpiry: 05/2027"
    r = client.post("/scan", data={"ocr_text": text, "crop": "cotton"}).json()
    assert r["identified"]["needs_confirmation"] and set(r["mismatch"]) == {"strength_pct", "formulation"}


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_photo_ocr_end_to_end_with_field_crops(client):
    png = label_png(["BLASTGUARD 75", "Tricyclazole 75% WP", "Reg. No: CIR-DEMO-1021",
                     "Batch No: BG25-221", "Expiry: 03/2027"])
    r = client.post("/scan", files={"image": ("label.png", png, "image/png")},
                    data={"crop": "rice", "pest": "blast"}).json()
    assert r["identified"]["ocr_engine"] == "tesseract"
    assert r["product"]["brand"] == "Blastguard 75", r["extracted"]
    assert r["extracted"]["batch"] == "BG25-221"
    assert r["field_checks"]["batch"]["crop_url"].startswith("/uploads/crops/")
    assert client.get(r["field_checks"]["batch"]["crop_url"]).status_code == 200
    assert r["image_url"].startswith("/uploads/pack/")


def test_admin_requires_token(client):
    assert client.get("/admin/bans").status_code == 401
    assert client.get("/admin/bans", headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_admin_adds_state_ban_that_takes_effect(client, pid):
    before = client.post("/scan", data={"product_id": pid("Spino 45"), "crop": "tomato", "pest": "fruit borer",
                                        "state": "karnataka"}).json()
    assert before["verdict"] == "green"
    ban = client.post("/admin/state-bans", headers=ADMIN, json={
        "state": "Karnataka", "crop": "tomato", "active_ingredient": "spinosad", "effective_from": "2026-01-01",
        "source_url": "https://example.gov.in/order-123"}).json()
    after = client.post("/scan", data={"product_id": pid("Spino 45"), "crop": "tomato", "pest": "fruit borer",
                                       "state": "karnataka"}).json()
    assert after["verdict"] == "red" and "R7" in [f["id"] for f in after["fired"]]
    assert client.delete(f"/admin/state-bans/{ban['id']}", headers=ADMIN).status_code == 200
    assert any(b["name"] == "phorate" for b in client.get("/admin/bans", headers=ADMIN).json()["national"])


def test_admin_national_ban_with_future_date(client, pid):
    later = date(date.today().year + 1, 1, 1).isoformat()
    client.put("/admin/ingredients/pymetrozine", headers=ADMIN, json={
        "banned": True, "banned_from": later, "source_url": "https://example.gov.in/gazette"})
    r = client.post("/scan", data={"product_id": pid("Pymet 50"), "crop": "rice", "pest": "bph"}).json()
    assert "R2" not in [f["id"] for f in r["fired"]]  # not in force yet
    client.put("/admin/ingredients/pymetrozine", headers=ADMIN, json={
        "banned": True, "banned_from": "2020-01-01", "source_url": "https://example.gov.in/gazette"})
    r = client.post("/scan", data={"product_id": pid("Pymet 50"), "crop": "rice", "pest": "bph"}).json()
    assert "R2" in [f["id"] for f in r["fired"]]
    client.put("/admin/ingredients/pymetrozine", headers=ADMIN, json={
        "banned": False, "source_url": "https://example.gov.in/gazette"})


def test_farmer_submission_and_admin_review(client):
    s = client.post("/products/submit", data={"brand": "Newbrand 20", "active_ingredient": "acetamiprid",
                                              "strength_pct": "20", "formulation": "sp", "user_id": "u9"},
                    files={"photo": ("p.jpg", b"\xff\xd8fakejpeg", "image/jpeg")}).json()
    pending = client.get("/admin/submissions", headers=ADMIN).json()
    assert any(p["id"] == s["submission_id"] and p["photo_url"] for p in pending)
    ok = client.post(f"/admin/submissions/{s['submission_id']}/approve", headers=ADMIN,
                     json={"toxicity_colour": "yellow", "company": "Reviewed Co"}).json()
    assert ok["status"] == "approved" and ok["product"]["formulation"] == "acetamiprid 20 SP"
    r = client.post("/scan", data={"product_id": ok["product"]["id"], "crop": "cotton", "pest": "aphid"}).json()
    assert r["verdict"] == "green"


def test_reminder_ics(client, pid):
    client.post("/spray-log", json={"plot_id": "ICS-1", "crop": "cotton", "pest": "bollworm",
                                    "product_id": pid("Emacure"), "spray_date": "2026-10-01"})
    r = client.get("/reminder.ics", params={"plot_id": "ICS-1"})
    assert r.status_code == 200 and "DTSTART;VALUE=DATE:20261011" in r.text and "BEGIN:VALARM" in r.text


def test_async_scan_job(client):
    png = label_png(["HEXA 5", "Hexaconazole 5% EC"])
    job = client.post("/scan/async", files={"image": ("l.png", png, "image/png")}, data={"crop": "rice"}).json()
    assert job["backend"] == "local"
    for _ in range(100):
        st = client.get(f"/jobs/{job['job_id']}").json()
        if st["status"] != "queued":
            break
        time.sleep(0.1)
    assert st["status"] == "done" and st["result"]["status"] in ("ok", "need_input")
    assert client.get("/jobs/local:nope").status_code == 404


def test_explain_retrieves_source_rows(client, pid):
    fired = [{"id": "R5", "message": "Not approved for cotton.", "message_en": "Not approved for cotton."}]
    r = client.post("/explain", json={"fired": fired, "product_id": pid("Blastguard 75"), "crop": "cotton"}).json()
    assert r["method"] == "template"
    assert any(row["table"] == "products" for row in r["source_rows"])
    assert any(row["table"] == "approved_options" for row in r["source_rows"])


def test_doctor_card_bilingual(client):
    r = client.get("/sos", params={"lang": "mr", "product_ids": "1"}).json()
    assert set(r["labels"]) == {"en", "mr"}
    assert r["labels"]["en"]["antidote"].startswith("Antidote") and r["labels"]["mr"]["title"] == "डॉक्टर कार्ड"


def test_report_photo_shown_in_batch_detail(client, pid):
    s = client.post("/scan", data={"product_id": pid("Tebu 25.9"), "fields": json.dumps({"batch": "TB-9"})}).json()
    client.post("/report", data={"scan_id": s["scan_id"], "reason": "cap broken"},
                files={"photo": ("r.jpg", b"\xff\xd8x", "image/jpeg")})
    d = client.get("/radar/batch", params={"batch": "TB-9"}).json()
    assert d["reports"][0]["photo_url"].startswith("/uploads/report/")


def test_shop_is_recorded_for_radar(client, pid):
    client.post("/scan", data={"product_id": pid("Azoxy 23"), "fields": json.dumps({"batch": "AZ-1"}),
                               "shop": "Krishi Kendra, Wardha", "district": "Wardha"})
    assert "Krishi Kendra, Wardha" in client.get("/radar/batch", params={"batch": "AZ-1"}).json()["shops"]


def test_enrichment_and_catalogue_sizes(client):
    from app.db import SessionLocal
    from app import models
    from sqlalchemy import func, select
    with SessionLocal() as db:
        grouped = db.scalar(select(func.count(models.ActiveIngredient.id)).where(
            models.ActiveIngredient.irac_frac_group.is_not(None)))
    assert grouped >= 60
    assert len(client.get("/products").json()) >= 50


def test_impact_metrics_and_report_confirmation(client, pid):
    items = [{"product_name": "Kavach Imida", "pack_size": "250 ml", "quantity": 1, "price": 720}]
    client.post("/bill", data={"items": json.dumps(items), "crop": "cotton", "user_id": "m1"})
    client.post("/spray-log", json={"plot_id": "MET-1", "crop": "cotton", "product_id": pid("Emacure"),
                                    "spray_date": "2026-09-01", "pest": "bollworm"})
    client.get("/passport/MET-1", params={"view": "true"})
    s = client.post("/scan", data={"product_id": pid("Cyper 10"), "fields": json.dumps({"batch": "CY-1"})}).json()
    rep = client.post("/report", data={"scan_id": s["scan_id"], "reason": "smell"}).json()
    assert client.put(f"/admin/reports/{rep['report_id']}", headers=ADMIN, data={"status": "confirmed"}).json()["status"] == "confirmed"
    m = client.get("/metrics").json()
    assert m["bills_checked"] >= 1 and m["money_saved_rs"] > 0 and m["money_saved_per_farmer_rs"] > 0
    assert m["sprays_with_safe_date"] >= 1 and m["passport_views_by_buyers"] >= 1
    assert m["reports_confirmed_by_officers"] >= 1 and 0 < m["red_share"] < 1


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_accuracy_harness_runs(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, str(root / "scripts" / "make_synthetic_packs.py"), str(tmp_path)], check=True)
    sys.path.insert(0, str(root / "scripts"))
    import accuracy_report
    packs = accuracy_report.run_packs(tmp_path / "packs")
    bills = accuracy_report.run_bills(tmp_path / "bills")
    assert packs["fields_acc"] >= 0.9 and packs["top1_acc"] >= 0.9 and bills["acc"] >= 0.9
    assert "Key fields exact" in accuracy_report.report(packs, bills)
