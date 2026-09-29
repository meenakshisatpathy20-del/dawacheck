"""QR decoding and payload parsing.

The Insecticides (First Amendment) Rules, 2025 require a QR with batch, dates,
a unique ID and licence details, but no single payload format is published.
We accept the common shapes: URL query strings, key:value / key=value lists,
JSON, and our own pipe format `QRID|BATCH|SERIAL`.
"""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse

KEYS = {
    "qr_id": ["uid", "uniqueid", "unique_id", "id", "qrid", "qr_id", "code"],
    "batch": ["batch", "batchno", "batch_no", "lot", "b"],
    "mfg_date": ["mfg", "mfd", "mfgdate", "mfg_date", "dom", "manufactured"],
    "exp_date": ["exp", "expiry", "expdate", "exp_date", "doe", "bestbefore"],
    "reg_no": ["reg", "regno", "reg_no", "cir", "registration", "registrationno"],
    "licence": ["lic", "licence", "license", "mfglic", "licno"],
    "brand": ["brand", "product", "name", "tradename"],
}


def decode_image(data: bytes) -> str | None:
    """Decode the first QR code in an image. Returns None if OpenCV is missing or no QR found."""
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return text or None


def _norm_key(k: str) -> str:
    return re.sub(r"[^a-z_]", "", k.lower().replace(" ", "").replace(".", ""))


def parse_payload(payload: str) -> dict:
    payload = (payload or "").strip()
    raw: dict[str, str] = {}
    if payload.startswith("{"):
        try:
            raw = {str(k): str(v) for k, v in json.loads(payload).items()}
        except ValueError:
            raw = {}
    elif payload.lower().startswith(("http://", "https://")):
        u = urlparse(payload)
        raw = {k: v[0] for k, v in parse_qs(u.query).items()}
        if not raw:
            raw = {"id": u.path.rstrip("/").rsplit("/", 1)[-1]}
    elif "|" in payload and ":" not in payload and "=" not in payload:
        parts = payload.split("|")
        raw = {"id": parts[0], "batch": parts[1] if len(parts) > 1 else "", "serial": parts[2] if len(parts) > 2 else ""}
    else:
        for part in re.split(r"[;\n|,]", payload):
            m = re.match(r"\s*([^:=]+)[:=]\s*(.+)", part)
            if m:
                raw[m.group(1).strip()] = m.group(2).strip()
    out: dict[str, str] = {}
    lookup = {alias: field for field, aliases in KEYS.items() for alias in aliases}
    for k, v in raw.items():
        field = lookup.get(_norm_key(k))
        if field and v:
            out[field] = v
    if "serial" in raw:
        out["serial"] = raw["serial"]
    out["raw"] = payload
    return out
