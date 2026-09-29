"""Vercel entry point: the complete FastAPI backend (backend/app) as one Python function.

vercel.json sends every /api/... request here. If Vercel hands the function its own
path (/api/index) instead of the original one, the original path is restored from
the ?__path= parameter that the rewrite adds. The backend answers both /api/x and /x.
"""
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi import FastAPI  # noqa: E402

from app.main import app as backend  # noqa: E402


class RestoreRewrittenPath:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            query = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
            wanted = [v for k, v in query if k == "__path"]
            if wanted:
                rest = urlencode([(k, v) for k, v in query if k != "__path"]).encode()
                scope = {**scope, "query_string": rest}
                if scope["path"].rstrip("/") in ("/api/index", "/api/index.py"):
                    path = "/api/" + wanted[0].lstrip("/")
                    scope = {**scope, "path": path, "raw_path": path.encode()}
        await self.inner(scope, receive, send)


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(RestoreRewrittenPath)
app.mount("/", backend)
