"""W6 Fake-Batch Radar: turn anonymous scans into batch signals.

Signals (playbook section 6):
  date_conflict   same product + batch seen with different mfg/expiry dates
  cloned_qr       same QR payload scanned in far-apart districts within a short time
  not_in_registry scans of products whose formulation is not registered
  farmer_report   farmers reported the batch

A signal never says "fake": it is a reason for an officer to inspect.
Recomputed from scratch; fine for pilot volumes, move to incremental jobs later.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import geo, models

CLONE_KM = 200
CLONE_WINDOW = timedelta(days=7)
SCORES = {"date_conflict": 1.0, "cloned_qr": 1.0, "not_in_registry": 0.5, "farmer_report": 0.5}


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def recompute(db: Session) -> int:
    db.execute(delete(models.BatchSignal))
    scans = list(db.scalars(select(models.Scan)))
    signals: list[models.BatchSignal] = []

    def add(kind, product_id, batch, rows, detail, extra=0.0):
        districts = sorted({r.district for r in rows if r.district})
        signals.append(models.BatchSignal(
            product_id=product_id, batch=batch, signal_type=kind, count=len(rows), districts=districts,
            first_seen=min(r.created_at for r in rows), last_seen=max(r.created_at for r in rows),
            score=round(SCORES[kind] + extra, 2), detail=detail))

    by_batch: dict[tuple, list[models.Scan]] = defaultdict(list)
    for s in scans:
        if s.product_id and s.batch:
            by_batch[(s.product_id, s.batch)].append(s)
    for (pid, batch), rows in by_batch.items():
        # Compare only dates that were actually read, at month precision (many labels print MM/YYYY).
        mfgs = {(r.mfg_date.year, r.mfg_date.month) for r in rows if r.mfg_date}
        exps = {(r.exp_date.year, r.exp_date.month) for r in rows if r.exp_date}
        if len(mfgs) > 1 or len(exps) > 1:
            add("date_conflict", pid, batch, rows,
                {"mfg_seen": sorted(f"{y}-{m:02d}" for y, m in mfgs), "exp_seen": sorted(f"{y}-{m:02d}" for y, m in exps)},
                extra=0.2 * (max(len(mfgs), len(exps)) - 2))

    for rows, km, h in _cloned_qr_groups(db, scans):
        add("cloned_qr", rows[0].product_id, rows[0].batch, rows, {"max_km": km, "qr_hash": h[:12]})

    unregistered = defaultdict(list)
    for s in scans:
        if s.product_id:
            p = db.get(models.Product, s.product_id)
            if p and not p.formulation.registered:
                unregistered[(s.product_id, s.batch)].append(s)
        elif s.fired_rules and "R1" in s.fired_rules:
            unregistered[(None, s.batch)].append(s)
    for (pid, batch), rows in unregistered.items():
        add("not_in_registry", pid, batch, rows, {})

    reports = defaultdict(list)
    for r in db.scalars(select(models.Report)):
        s = db.get(models.Scan, r.scan_id) if r.scan_id else None
        if s:
            reports[(s.product_id, s.batch)].append((r, s))
    for (pid, batch), pairs in reports.items():
        add("farmer_report", pid, batch, [s for _, s in pairs], {"reasons": [r.reason for r, _ in pairs]},
            extra=0.5 * (len(pairs) - 1))

    db.add_all(signals)
    db.flush()
    return len(signals)


def _cloned_qr_groups(db: Session, scans: list[models.Scan]):
    """Same QR payload scanned >= CLONE_KM apart within CLONE_WINDOW. PostGIS when available."""
    by_id = {s.id: s for s in scans}
    groups: dict[str, dict] = {}
    if geo.available():
        db.flush()
        for a_id, b_id, km in geo.cloned_qr_pairs(db, CLONE_KM, CLONE_WINDOW):
            a, b = by_id[a_id], by_id[b_id]
            g = groups.setdefault(a.qr_payload_hash, {"rows": {}, "km": 0.0})
            g["rows"][a.id], g["rows"][b.id] = a, b
            g["km"] = max(g["km"], km)
    else:
        by_qr: dict[str, list[models.Scan]] = defaultdict(list)
        for s in scans:
            if s.qr_payload_hash and s.lat is not None:
                by_qr[s.qr_payload_hash].append(s)
        for h, rows in by_qr.items():
            rows.sort(key=lambda r: r.created_at)
            for i, a in enumerate(rows):
                for b in rows[i + 1:]:
                    km = haversine_km((a.lat, a.lon), (b.lat, b.lon))
                    if b.created_at - a.created_at <= CLONE_WINDOW and km >= CLONE_KM:
                        g = groups.setdefault(h, {"rows": {}, "km": 0.0})
                        g["rows"][a.id], g["rows"][b.id] = a, b
                        g["km"] = max(g["km"], km)
    return [(sorted(g["rows"].values(), key=lambda r: r.created_at), round(g["km"]), h) for h, g in groups.items()]


def signal_for(db: Session, product_id: int | None, batch: str | None) -> dict | None:
    """Strongest signal for this batch (feeds rule R8)."""
    if not batch:
        return None
    q = select(models.BatchSignal).where(models.BatchSignal.batch == batch)
    if product_id:
        q = q.where(models.BatchSignal.product_id == product_id)
    rows = list(db.scalars(q))
    if not rows:
        return None
    s = max(rows, key=lambda r: r.score)
    return {"batch": s.batch, "signal_type": s.signal_type, "score": s.score, "count": s.count}


def _product_label(db: Session, pid: int | None) -> str:
    p = db.get(models.Product, pid) if pid else None
    return f"{p.brand} ({p.formulation.label})" if p else "unknown product"


def dashboard(db: Session, district: str | None = None, days: int = 90) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    scans = [s for s in db.scalars(select(models.Scan).where(models.Scan.created_at >= since))
             if not district or s.district == district]
    signals = list(db.scalars(select(models.BatchSignal)))
    flagged = {(s.product_id, s.batch) for s in signals if s.score >= 1.0}

    clusters: dict[str, dict] = {}
    for s in scans:
        if not s.district or s.lat is None:
            continue
        c = clusters.setdefault(s.district, {"district": s.district, "lat": 0.0, "lon": 0.0, "n": 0,
                                             "scans": 0, "red": 0, "flagged": 0})
        c["lat"] += s.lat
        c["lon"] += s.lon
        c["n"] += 1
        c["scans"] += 1
        c["red"] += 1 if s.verdict == "red" else 0
        c["flagged"] += 1 if (s.product_id, s.batch) in flagged else 0
    centroids = geo.district_centroids(db, since) if geo.available() else {}
    for c in clusters.values():
        c["lat"], c["lon"] = centroids.get(c["district"], (c["lat"] / c["n"], c["lon"] / c["n"]))
        c["risk"] = "red" if c["flagged"] or c["red"] else "green"
        del c["n"]

    ranked = sorted(signals, key=lambda s: (-s.score, -s.count))
    batches = [{
        "id": s.id, "product": _product_label(db, s.product_id), "product_id": s.product_id, "batch": s.batch,
        "signal_type": s.signal_type, "districts": s.districts, "count": s.count, "score": s.score,
        "first_seen": s.first_seen.isoformat(), "last_seen": s.last_seen.isoformat(), "detail": s.detail,
    } for s in ranked if not district or district in (s.districts or [])]
    return {
        "clusters": sorted(clusters.values(), key=lambda c: -(c["flagged"] + c["red"])),
        "batches": batches,
        "totals": {"scans": len(scans), "red": sum(1 for s in scans if s.verdict == "red"),
                   "yellow": sum(1 for s in scans if s.verdict == "yellow"),
                   "flagged_batches": len({(b["product_id"], b["batch"]) for b in batches if b["score"] >= 1.0})},
        "note": "Signals are reasons to inspect, not proof. Only a lab test shows a product is spurious.",
        "geo_engine": "postgis" if geo.available() else "python",
    }


def batch_detail(db: Session, product_id: int | None, batch: str) -> dict:
    q = select(models.Scan).where(models.Scan.batch == batch)
    if product_id:
        q = q.where(models.Scan.product_id == product_id)
    scans = sorted(db.scalars(q), key=lambda s: s.created_at)
    reports = [r for r in db.scalars(select(models.Report)) if r.scan_id in {s.id for s in scans}]
    return {
        "product": _product_label(db, product_id), "batch": batch,
        "timeline": [{"at": s.created_at.isoformat(), "district": s.district, "shop": s.shop,
                      "mfg_date": str(s.mfg_date) if s.mfg_date else None,
                      "exp_date": str(s.exp_date) if s.exp_date else None, "verdict": s.verdict} for s in scans],
        "dates_seen": sorted({f"{s.mfg_date or '?'} / {s.exp_date or '?'}" for s in scans if s.mfg_date or s.exp_date}),
        "shops": sorted({s.shop for s in scans if s.shop}),
        "reports": [{"reason": r.reason, "photo_url": r.photo_url, "status": r.status,
                     "at": r.created_at.isoformat()} for r in reports],
    }
