"""Background queue on Vercel (Upstash QStash): signed callback, stored job, polling."""
import base64
import hashlib
import hmac
import json
import time

import pytest

from app import config, jobs


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def sign(body: bytes, key="sig-current", **over) -> str:
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = {"iss": "Upstash", "sub": "https://x.vercel.app/api/jobs/run", "exp": time.time() + 300,
              "nbf": time.time() - 1, "iat": time.time(), "jti": "j",
              "body": _b64(hashlib.sha256(body).digest())} | over
    c = _b64(json.dumps(claims).encode())
    s = _b64(hmac.new(key.encode(), f"{head}.{c}".encode(), hashlib.sha256).digest())
    return f"{head}.{c}.{s}"


@pytest.fixture
def qstash(monkeypatch):
    monkeypatch.setattr(config, "QSTASH_TOKEN", "tok")
    monkeypatch.setattr(config, "PUBLIC_URL", "https://x.vercel.app")
    monkeypatch.setattr(config, "QSTASH_CURRENT_SIGNING_KEY", "sig-current")
    monkeypatch.setattr(config, "QSTASH_NEXT_SIGNING_KEY", "sig-next")
    monkeypatch.setattr(config, "DATABASE_URL", "postgresql+psycopg://shared/db")
    sent = []

    class Resp:
        def raise_for_status(self):
            pass

    import httpx
    monkeypatch.setattr(httpx, "post", lambda url, **kw: sent.append((url, kw)) or Resp())
    return sent


def test_signature_checks():
    body = b'{"job_id": "a"}'
    config_keys = (config.QSTASH_CURRENT_SIGNING_KEY, config.QSTASH_NEXT_SIGNING_KEY)
    try:
        config.QSTASH_CURRENT_SIGNING_KEY, config.QSTASH_NEXT_SIGNING_KEY = "sig-current", "sig-next"
        assert jobs.verify_qstash(sign(body), body)
        assert jobs.verify_qstash(sign(body, key="sig-next"), body)
        assert not jobs.verify_qstash(sign(body, key="wrong"), body)
        assert not jobs.verify_qstash(sign(body), b'{"job_id": "b"}')
        assert not jobs.verify_qstash(sign(body, exp=time.time() - 60), body)
        assert not jobs.verify_qstash(sign(body, iss="someone"), body)
        assert not jobs.verify_qstash(None, body)
    finally:
        config.QSTASH_CURRENT_SIGNING_KEY, config.QSTASH_NEXT_SIGNING_KEY = config_keys


def test_qstash_job_round_trip(client, qstash):
    out = jobs.submit("scan", {"product_id": 1, "crop": "cotton", "image": b"\x00\x01"})
    assert out["backend"] == "qstash" and out["job_id"].startswith("qs:")
    url, kw = qstash[0]
    assert url == "https://qstash.upstash.io/v2/publish/https://x.vercel.app/api/jobs/run"
    assert kw["headers"]["Authorization"] == "Bearer tok"
    assert client.get(f"/jobs/{out['job_id']}").json() == {"status": "queued"}

    body = json.dumps(kw["json"]).encode()
    assert client.post("/jobs/run", content=body).status_code == 401
    r = client.post("/jobs/run", content=body, headers={"Upstash-Signature": sign(body)})
    assert r.status_code == 200 and r.json()["status"] == "done"
    st = client.get(f"/jobs/{out['job_id']}").json()
    assert st["status"] == "done" and st["result"]["status"] == "ok"


def test_qstash_needs_shared_database(monkeypatch):
    monkeypatch.setattr(config, "QSTASH_TOKEN", "tok")
    monkeypatch.setattr(config, "PUBLIC_URL", "https://x.vercel.app")
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:////tmp/x.db")
    assert not jobs.qstash_enabled()


def test_publish_failure_falls_back_inline(client, qstash, monkeypatch):
    import httpx

    def boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(httpx, "post", boom)
    monkeypatch.setattr(config, "SERVERLESS", True)
    out = jobs.submit("scan", {"product_id": 1, "crop": "cotton"})
    assert out["backend"] == "inline" and out["status"] == "done"
