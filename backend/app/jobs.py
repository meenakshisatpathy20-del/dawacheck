"""Queue for slow OCR jobs (playbook section 11: 'Redis: queue slow OCR jobs').

With REDIS_URL set, jobs go to an RQ queue served by the `worker` container
(`rq worker ocr`). Without Redis (laptop, tests) they run in a local thread
pool. Either way the app polls GET /jobs/{id}.
"""
from __future__ import annotations

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


def submit(kind: str, kwargs: dict) -> dict:
    fn = _FUNCS[kind]
    q = _rq_queue()
    if q is not None:
        job = q.enqueue(fn, kwargs, job_timeout=120, result_ttl=3600)
        return {"job_id": f"rq:{job.id}", "backend": "redis"}
    jid = f"local:{uuid.uuid4().hex}"
    _local[jid] = _pool.submit(fn, kwargs)
    return {"job_id": jid, "backend": "local"}


def status(job_id: str) -> dict | None:
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
