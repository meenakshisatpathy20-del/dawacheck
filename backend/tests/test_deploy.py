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


def test_photos_served_by_backend_from_disk_and_bucket(client, monkeypatch):
    from app.services import storage

    # Local disk
    s = client.post("/report", data={"reason": "photo test"}, files={"photo": ("r.jpg", jpeg(), "image/jpeg")}).json()
    assert s["status"] == "ok"
    digest, url = storage.save_image(jpeg(), "report")
    assert url == f"/uploads/report/{digest}.jpg"
    r = client.get(url)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get("/api" + url).status_code == 200  # through the Vercel /api prefix too

    # S3-compatible bucket (a fake client stands in for R2 / S3 / MinIO)
    bucket = {}

    class FakeS3:
        def put_object(self, Bucket, Key, Body, ContentType):
            bucket[Key] = Body

        def get_object(self, Bucket, Key):
            return {"Body": io.BytesIO(bucket[Key])}

    monkeypatch.setattr(config, "S3_ENDPOINT", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setattr(storage, "_s3", lambda: FakeS3())
    img = jpeg() + b"bucket"
    digest, url = storage.save_image(img, "pack")
    assert url.startswith("/uploads/pack/") and f"pack/{digest}.jpg" in bucket
    assert client.get(url).content == img

    # Invalid names never touch the disk or bucket
    assert client.get("/uploads/pack/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/uploads/secret/" + "a" * 64 + ".jpg").status_code == 404


def test_weather_window_uses_field_local_time(monkeypatch):
    """Server clock is UTC; the forecast is in local time (IST = +5:30). Start at the local hour."""
    from datetime import datetime, timedelta, timezone

    import httpx

    from app.services import weather
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    local = now_utc + timedelta(seconds=19800)
    base = local.replace(minute=0, second=0, microsecond=0) - timedelta(hours=10)
    times = [(base + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(30)]

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            n = len(times)
            return {"utc_offset_seconds": 19800, "hourly": {"time": times, "precipitation": [0] * n,
                    "precipitation_probability": [0] * n, "wind_speed_10m": [0] * n, "temperature_2m": [25] * n}}
    monkeypatch.setattr(config, "OFFLINE", False)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: R())
    out = weather.fetch(19.0, 73.0)
    assert out["hours"][0]["time"] == local.strftime("%H:00")


def test_prefixed_vercel_storage_variable_is_found(monkeypatch):
    for k in ("DATABASE_URL", "POSTGRES_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("STORAGE_DATABASE_URL", "postgres://u:p@h/db?sslmode=require")
    assert config._db_url(config._find_db_env()) == "postgresql+psycopg://u:p@h/db?sslmode=require"
