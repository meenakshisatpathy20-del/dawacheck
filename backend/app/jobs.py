"""Queue for slow OCR jobs (playbook section 11: 'Redis: queue slow OCR jobs').

Backends, first that is available wins:
- Redis (REDIS_URL): an RQ queue served by `rq worker ocr` (its own container, or
  started next to the API by scripts/start.sh with RUN_WORKER=1).
- Upstash QStash (QSTASH_TOKEN, on Vercel): the job is stored in the `jobs` table and
  QStash calls the signed POST /jobs/run, which runs it in a separate function call.
- Serverless without a queue: the job runs inside the request.
- Otherwise (laptop, tests): a local thread pool.
The app polls GET /jobs/{id} in every case.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor

from . import config

QUEUE = "ocr"
_pool = ThreadPoolExecutor(max_workers=2)
_local: dict[str, Future] = {}


def run_scan_job(kwargs: dict) -> dict:
    """Executed by the worker: a normal scan in its own DB session."""
    from .db import SessionLocal
    from .services import scan

    with SessionLocal() as db:
        return scan.scan(db, **kwargs)


def run_bill_job(kwargs: dict) -> dict:
    from .db import SessionLocal
    from .services import bill

    with SessionLocal() as db:
        return bill.check_bill(db, **kwargs)


_FUNCS = {"scan": run_scan_job, "bill": run_bill_job}


def _rq_queue():
    if not config.REDIS_URL:
        return None
    try:
        from redis import Redis
        from rq import Queue

        conn = Redis.from_url(config.REDIS_URL, socket_connect_timeout=1)
        conn.ping()
        return Queue(QUEUE, connection=conn)
    except Exception:
        return None


# ---------- QStash ----------

def qstash_enabled() -> bool:
    # Needs a database every function instance shares (not the per-instance SQLite in /tmp).
    return bool(config.QSTASH_TOKEN and config.PUBLIC_URL and not config.DATABASE_URL.startswith("sqlite"))


def _pack(kwargs: dict) -> dict:
    return {k: {"__b64__": base64.b64encode(v).decode()} if isinstance(v, (bytes, bytearray)) else v
            for k, v in kwargs.items()}


def _unpack(payload: dict) -> dict:
    return {k: base64.b64decode(v["__b64__"]) if isinstance(v, dict) and "__b64__" in v else v
            for k, v in payload.items()}


def _json_safe(obj):
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(obj)


def _qstash_submit(kind: str, kwargs: dict) -> dict | None:
    import httpx

    from . import models
    from .db import SessionLocal

    jid = uuid.uuid4().hex
    with SessionLocal() as db:
        db.add(models.Job(id=jid, kind=kind, payload=_pack(kwargs)))
        db.commit()
    target = f"{config.PUBLIC_URL}/api/jobs/run"
    try:
        r = httpx.post(f"{config.QSTASH_URL}/v2/publish/{target}", json={"job_id": jid},
                       headers={"Authorization": f"Bearer {config.QSTASH_TOKEN}", "Upstash-Retries": "2"},
                       timeout=10)
        r.raise_for_status()
    except Exception:
        with SessionLocal() as db:
            job = db.get(models.Job, jid)
            db.delete(job)
            db.commit()
        return None
    return {"job_id": f"qs:{jid}", "backend": "qstash"}


def _b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def verify_qstash(signature: str | None, body: bytes, url: str | None = None) -> bool:
    """Check the Upstash-Signature JWT (HS256, current or next signing key)."""
    if not signature:
        return False
    try:
        head, claims_b64, sig_b64 = signature.split(".")
    except ValueError:
        return False
    for key in (config.QSTASH_CURRENT_SIGNING_KEY, config.QSTASH_NEXT_SIGNING_KEY):
        if not key:
            continue
        expected = hmac.new(key.encode(), f"{head}.{claims_b64}".encode(), hashlib.sha256).digest()
        try:
            if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
                continue
            header = json.loads(_b64url_decode(head))
            claims = json.loads(_b64url_decode(claims_b64))
        except Exception:
            continue
        now = time.time()
        body_hash = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip("=")
        if (header.get("alg") == "HS256" and claims.get("iss") == "Upstash"
                and claims.get("exp", 0) > now - 5 and claims.get("nbf", 0) <= now + 5
                and str(claims.get("body", "")).rstrip("=") == body_hash
                and (url is None or not claims.get("sub") or claims["sub"] == url)):
            return True
    return False


def run_stored(job_id: str) -> dict | None:
    """Run a job from the `jobs` table (called by QStash through POST /jobs/run)."""
    from . import models
    from .db import SessionLocal

    with SessionLocal() as db:
        job = db.get(models.Job, job_id)
        if job is None:
            return None
        if job.status in ("done", "failed"):
            return {"status": job.status}
        kind, payload = job.kind, job.payload
    try:
        result, err = _json_safe(_FUNCS[kind](_unpack(payload))), None
    except Exception as e:  # recorded for the poller; QStash does not need to retry a bad photo
        result, err = None, str(e) or type(e).__name__
    with SessionLocal() as db:
        job = db.get(models.Job, job_id)
        job.status, job.result, job.error = ("failed", None, err) if err else ("done", result, None)
        job.payload = {}  # drop the photo once read
        db.commit()
        return {"status": job.status}


def _qstash_status(jid: str) -> dict | None:
    from . import models
    from .db import SessionLocal

    with SessionLocal() as db:
        job = db.get(models.Job, jid)
        if job is None:
            return None
        if job.status == "done":
            return {"status": "done", "result": job.result}
        if job.status == "failed":
            return {"status": "failed", "error": job.error or "OCR job failed"}
        return {"status": "queued"}


def submit(kind: str, kwargs: dict) -> dict:
    fn = _FUNCS[kind]
    q = _rq_queue()
    if q is not None:
        job = q.enqueue(fn, kwargs, job_timeout=120, result_ttl=3600)
        return {"job_id": f"rq:{job.id}", "backend": "redis"}
    if qstash_enabled():
        out = _qstash_submit(kind, kwargs)
        if out is not None:
            return out
    jid = f"local:{uuid.uuid4().hex}"
    if config.SERVERLESS:
        # No shared memory between serverless instances: a later poll may reach another one,
        # so run the job inside this request and hand the result straight back.
        return {"job_id": jid, "backend": "inline", "status": "done", "result": fn(kwargs)}
    _local[jid] = _pool.submit(fn, kwargs)
    return {"job_id": jid, "backend": "local"}


def status(job_id: str) -> dict | None:
    if job_id.startswith("qs:"):
        return _qstash_status(job_id[3:])
    if job_id.startswith("local:"):
        fut = _local.get(job_id)
        if fut is None:
            return None
        if not fut.done():
            return {"status": "queued"}
        err = fut.exception()
        return {"status": "failed", "error": str(err)} if err else {"status": "done", "result": fut.result()}
    if job_id.startswith("rq:"):
        q = _rq_queue()
        if q is None:
            return None
        from rq.job import Job

        try:
            job = Job.fetch(job_id[3:], connection=q.connection)
        except Exception:
            return None
        st = job.get_status()
        if st == "finished":
            return {"status": "done", "result": job.return_value()}
        if st == "failed":
            return {"status": "failed", "error": "OCR job failed"}
        return {"status": "queued"}
    return None
