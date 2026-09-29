"""Deployment paths: hosted Postgres URLs, serverless job handling, vision fallback for
photos when no OCR engine is installed, and the Vercel entry point's path restore."""
import io
import sys
from pathlib import Path

from app import config, jobs
from app.ai import extract, ocr


def jpeg() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (60, 40), "white").save(b, format="JPEG")
    return b.getvalue()


def test_hosted_postgres_urls_use_psycopg3():
    assert config._db_url("postgres://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert config._db_url("postgresql://u@h/db") == "postgresql+psycopg://u@h/db"
    assert config._db_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert config._db_url("sqlite:////tmp/x.db") == "sqlite:////tmp/x.db"


def test_serverless_jobs_run_inline(monkeypatch):
    monkeypatch.setattr(config, "SERVERLESS", True)
    out = jobs.submit("scan", {"product_id": 1, "crop": "cotton"})
    assert out["backend"] == "inline" and out["status"] == "done" and out["result"]["status"] == "ok"


def test_vision_fallback_reads_label_when_no_ocr_engine(client, monkeypatch):
    monkeypatch.setattr(ocr, "read_lines", lambda data: ([], None))
    monkeypatch.setattr(extract, "llm_enabled", lambda: True)
    seen = {}

    def fake_llm(content, schema):
        seen["image"] = content[0]["type"] == "image" and content[0]["source"]["media_type"] == "image/jpeg"
        return {"brand": "BLASTGUARD 75", "active_ingredient": "tricyclazole", "strength_pct": 75,
                "formulation": "WP", "batch": None, "mfg_date": None, "exp_date": None, "reg_no": None,
                "manufacturer": None, "toxicity_colour": None,
                "lines": ["BLASTGUARD 75", "Tricyclazole 75% WP", "Batch No: BG25-221", "Expiry: 03/2027"]}

    monkeypatch.setattr(extract, "_llm_json", fake_llm)
    r = client.post("/scan", files={"image": ("p.jpg", jpeg(), "image/jpeg")}, data={"crop": "rice", "pest": "blast"}).json()
    assert seen["image"] and r["identified"]["ocr_engine"] == "vision"
    assert r["product"]["brand"] == "Blastguard 75"
    assert r["extracted"]["batch"] == "BG25-221"  # regex cross-check on the lines the model read
    assert r["verdict"] == "green"


def test_vision_fallback_for_bills(client, monkeypatch):
    monkeypatch.setattr(ocr, "read_text", lambda data: (None, None))
    monkeypatch.setattr(extract, "llm_enabled", lambda: True)
    monkeypatch.setattr(extract, "_llm_json", lambda content, schema: {
        "items": [{"product_name": "Blastguard 75", "pack_size": "120 g", "quantity": 1, "price": 290}], "total": 290})
    r = client.post("/bill", files={"image": ("b.jpg", jpeg(), "image/jpeg")}, data={"crop": "cotton"}).json()
    assert r["method"] == "vision" and r["items"][0]["verdict"] == "yellow"


def test_no_engine_and_no_llm_asks_for_other_input(client, monkeypatch):
    monkeypatch.setattr(ocr, "read_lines", lambda data: ([], None))
    monkeypatch.setattr(extract, "llm_enabled", lambda: False)
    r = client.post("/scan", files={"image": ("p.jpg", jpeg(), "image/jpeg")}).json()
    assert r["status"] == "need_input"


def test_api_prefix_serves_every_route(client):
    """Vercel mounts the backend service under /api; both /api/x and /x must reach the same route."""
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/health").json()["status"] == "ok"
    d = client.get("/api/radar/batch", params={"batch": "PF24-117"}).json()
    assert d["batch"] == "PF24-117"
    r = client.post("/api/scan", data={"qr_payload": "DC-QR-1012|EM25-777|0001", "crop": "cotton", "pest": "bollworm"}).json()
    assert r["verdict"] == "green"
    assert client.get("/api/docs").status_code == 200 and client.get("/api/openapi.json").status_code == 200


def test_backend_entry_point_for_vercel():
    import main  # backend/main.py, the file Vercel's FastAPI service looks for
    from app.main import app
    assert main.app is app
