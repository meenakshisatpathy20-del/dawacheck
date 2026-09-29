"""Entry point for hosts that look for `app` in main.py (Vercel's FastAPI service, `uvicorn main:app`).

The application itself is backend/app/main.py; this file only re-exports it.
"""
from app.main import app  # noqa: F401
