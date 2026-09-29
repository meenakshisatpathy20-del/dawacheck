"""Catalogue lookup cache: Redis when REDIS_URL is set, else in-process dict."""
from __future__ import annotations

import json
import time

from .. import config

_TTL = 600
_local: dict[str, tuple[float, object]] = {}
_redis = None

if config.REDIS_URL:
    try:
        import redis  # type: ignore

        _redis = redis.Redis.from_url(config.REDIS_URL, socket_connect_timeout=1)
        _redis.ping()
    except Exception:  # Redis down -> fall back to local cache, never break a scan
        _redis = None


def get(key: str):
    if _redis is not None:
        try:
            raw = _redis.get(f"dc:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            pass
    hit = _local.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def set(key: str, value) -> None:
    if _redis is not None:
        try:
            _redis.setex(f"dc:{key}", _TTL, json.dumps(value, default=str))
            return
        except Exception:
            pass
    _local[key] = (time.time() + _TTL, value)


def clear() -> None:
    _local.clear()
    if _redis is not None:
        try:
            for k in _redis.scan_iter("dc:*"):
                _redis.delete(k)
        except Exception:
            pass
