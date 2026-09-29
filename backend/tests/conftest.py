import os
import sys
import tempfile
from pathlib import Path

_DB = Path(tempfile.mkdtemp()) / "test.db"
# TEST_DATABASE_URL=postgresql+psycopg://... runs the same suite against PostgreSQL.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_DB}")
os.environ["DAWACHECK_OFFLINE"] = "1"
os.environ["LLM_ENABLED"] = "off"
os.environ["UPLOAD_DIR"] = str(_DB.parent / "uploads")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.seed import reset_and_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded():
    return reset_and_seed()


@pytest.fixture()
def db():
    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


@pytest.fixture()
def pid(db):
    def _pid(brand: str) -> int:
        return db.scalar(select(models.Product).where(models.Product.brand == brand)).id
    return _pid


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        yield c
