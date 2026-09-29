"""Geo queries: PostGIS on PostgreSQL (docker compose), plain Python on SQLite.

Scans keep lat/lon columns; PostGIS builds points on the fly and a GiST
expression index makes distance queries fast.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import engine

log = logging.getLogger(__name__)
_available: bool | None = None


def init() -> bool:
    """Enable PostGIS and the spatial index if the database supports it."""
    global _available
    if engine.dialect.name != "postgresql":
        _available = False
        return False
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS scans_geog_idx ON scans USING GIST "
                "((ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography)) WHERE lat IS NOT NULL"))
        _available = True
    except Exception as e:  # extension not installed: keep working without it
        log.warning("PostGIS unavailable (%s); using Python geo fallback", e.__class__.__name__)
        _available = False
    return _available


def available() -> bool:
    return init() if _available is None else _available


def cloned_qr_pairs(db: Session, min_km: float, window: timedelta) -> list[tuple[int, int, float]]:
    """(scan_a, scan_b, km) for the same QR payload seen far apart within the window. PostGIS only."""
    rows = db.execute(text("""
        SELECT a.id, b.id,
               ST_DistanceSphere(ST_MakePoint(a.lon, a.lat), ST_MakePoint(b.lon, b.lat)) / 1000.0 AS km
        FROM scans a JOIN scans b
          ON a.qr_payload_hash = b.qr_payload_hash AND a.id < b.id
        WHERE a.lat IS NOT NULL AND b.lat IS NOT NULL
          AND abs(extract(epoch FROM (b.created_at - a.created_at))) <= :window
          AND ST_DistanceSphere(ST_MakePoint(a.lon, a.lat), ST_MakePoint(b.lon, b.lat)) >= :min_m
    """), {"window": window.total_seconds(), "min_m": min_km * 1000}).all()
    return [(r[0], r[1], float(r[2])) for r in rows]


def district_centroids(db: Session, since: datetime) -> dict[str, tuple[float, float]]:
    """Centroid of scan points per district. PostGIS only."""
    rows = db.execute(text("""
        SELECT district, ST_Y(ST_Centroid(ST_Collect(ST_MakePoint(lon, lat)))) AS lat,
                         ST_X(ST_Centroid(ST_Collect(ST_MakePoint(lon, lat)))) AS lon
        FROM scans WHERE district IS NOT NULL AND lat IS NOT NULL AND created_at >= :since
        GROUP BY district
    """), {"since": since}).all()
    return {r[0]: (float(r[1]), float(r[2])) for r in rows}
