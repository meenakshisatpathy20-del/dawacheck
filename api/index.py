"""Vercel serverless entry point: the whole FastAPI backend as one Python function.

vercel.json rewrites every API path (/scan, /radar, /docs, ...) here and passes
the original path as ?__path=...; the React app is served as static files under /app/.
"""
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi import FastAPI  # noqa: E402

from app import geo, seed  # noqa: E402
from app.main import app as backend  # noqa: E402


class RestoreRewrittenPath:
    """If the platform delivers the rewritten URL (/api/index?__path=scan) instead of the
    original one (/scan), put the original path back before FastAPI routes the request."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            query = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
            wanted = [v for k, v in query if k == "__path"]
            rest = [(k, v) for k, v in query if k != "__path"]
            if wanted and scope["path"].startswith("/api/index"):
                path = "/" + wanted[0].lstrip("/")
                scope = {**scope, "path": path, "raw_path": path.encode()}
            if wanted:
                scope = {**scope, "query_string": urlencode(rest).encode()}
        await self.inner(scope, receive, send)


# A fresh parent app (Vercel looks for `app`): the whole backend is mounted at "/", unchanged.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(RestoreRewrittenPath)
app.mount("/", backend)

# Serverless functions may not run ASGI lifespan events: prepare the database on cold start instead.
seed.ensure_seeded()
geo.init()
