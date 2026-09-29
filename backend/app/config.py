"""Runtime settings, read from environment variables (see .env.example)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'backend' / 'dawacheck.db'}")
SEED_DIR = Path(os.getenv("SEED_DIR", ROOT / "data" / "seed"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", ROOT / "backend" / "uploads"))
REDIS_URL = os.getenv("REDIS_URL", "")

# S3 / MinIO for pack and bill photos. Local disk is used when S3_ENDPOINT is empty.
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_BUCKET = os.getenv("S3_BUCKET", "dawacheck")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")

# LLM used ONLY for turning OCR text into JSON and for plain-language rephrasing.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
LLM_ENABLED = os.getenv("LLM_ENABLED", "auto")  # auto | on | off

# Salt for hashing phone numbers / device ids. Change in production.
USER_HASH_SALT = os.getenv("USER_HASH_SALT", "dawacheck-dev-salt")

OPEN_METEO_URL = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
OFFLINE = os.getenv("DAWACHECK_OFFLINE", "0") == "1"  # skip all outbound calls (tests, stage)

NEAR_EXPIRY_DAYS = int(os.getenv("NEAR_EXPIRY_DAYS", "30"))
DEFAULT_TANK_L = float(os.getenv("DEFAULT_TANK_L", "15"))
