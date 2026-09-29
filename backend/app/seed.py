"""Load backend/data/seed/*.json into the database.  `python -m app.seed [--reset]`

Parsed CIB&RC data from pipeline/ is loaded the same way: pipeline/load.py
writes label_claims.json in this format and calls load_all().
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config, models, normalise
from .db import Base, SessionLocal, engine


def _read(name: str, seed_dir: Path) -> dict:
    return json.loads((seed_dir / name).read_text(encoding="utf-8"))


def _formulation(db: Session, ai: models.ActiveIngredient, pct: float, ftype: str, registered: bool = True,
                 source_file: str | None = None, page: int | None = None) -> models.Formulation:
    f = db.scalar(select(models.Formulation).where(
        models.Formulation.active_ingredient_id == ai.id,
        models.Formulation.strength_pct == float(pct),
        models.Formulation.type == ftype.upper()))
    if f is None:
        f = models.Formulation(active_ingredient=ai, strength_pct=float(pct), type=ftype.upper(),
                               registered=registered, source_file=source_file, page=page)
        db.add(f)
        db.flush()
    return f


def load_all(db: Session, seed_dir: Path = config.SEED_DIR, demo_scans: bool = True) -> dict:
    counts: dict[str, int] = {}

    ais = _read("active_ingredients.json", seed_dir)
    defaults = ais.get("defaults", {})
    by_name: dict[str, models.ActiveIngredient] = {}
    for it in ais["items"]:
        ai = models.ActiveIngredient(
            name=it["name"], synonyms=it.get("synonyms", []), chem_class=it.get("chem_class"), kind=it.get("kind"),
            irac_frac_group=it.get("irac_frac_group"), moa_scheme=it.get("moa_scheme"),
            toxicity_colour=it.get("toxicity_colour"), banned=it.get("banned", False),
            restricted=it.get("restricted", False), ban_note=it.get("ban_note"),
            antidote_text=it.get("antidote_text"), first_aid_text=it.get("first_aid_text", defaults.get("first_aid_text")),
            source_url=it.get("source_url", defaults.get("source_url")))
        db.add(ai)
        by_name[ai.name] = ai
    db.flush()
    counts["active_ingredients"] = len(by_name)

    def get_ai(name: str) -> models.ActiveIngredient:
        """Chemicals found in parsed PDFs but missing from the enrichment table are created bare
        (no IRAC/FRAC group or colour) so they still get registry and label-claim checks."""
        key = normalise.ingredient(name)
        if key not in by_name:
            by_name[key] = models.ActiveIngredient(name=key, first_aid_text=defaults.get("first_aid_text"),
                                                   source_url=defaults.get("source_url"))
            db.add(by_name[key])
            db.flush()
        return by_name[key]

    claims = _read("label_claims.json", seed_dir)
    n = 0
    for it in claims["items"]:
        ai = get_ai(it["ai"])
        f = _formulation(db, ai, it["pct"], it["type"])
        ai_lo, ai_hi = normalise.parse_range(it.get("ai_g_ha"))
        fo_lo, fo_hi = normalise.parse_range(it.get("form_ha"))
        pests = it["pests"] if isinstance(it["pests"], list) else normalise.split_pests(it["pests"])
        for pest in pests:
            db.add(models.LabelClaim(
                formulation=f, crop=normalise.crop(it["crop"]), pest=normalise.pest(pest),
                dose_ai_g_ha_min=ai_lo, dose_ai_g_ha_max=ai_hi, dose_form_ha_min=fo_lo, dose_form_ha_max=fo_hi,
                unit=it.get("unit", "ml"), water_l_ha=it.get("water_l_ha"), phi_days=it.get("phi_days"),
                source_file=it.get("source_file", claims.get("source_file")), page=it.get("page"),
                verified=it.get("verified", False)))
            n += 1
    counts["label_claims"] = n

    prods = _read("products.json", seed_dir)
    by_brand: dict[str, models.Product] = {}
    for it in prods["items"]:
        ai = get_ai(it["ai"])
        f = _formulation(db, ai, it["pct"], it["type"], registered=it.get("formulation_registered", True))
        p = models.Product(brand=it["brand"], company=it.get("company"), formulation=f, reg_no=it.get("reg_no"),
                           pack_sizes=it.get("pack_sizes", []), toxicity_colour=it.get("toxicity_colour"),
                           mrp=it.get("mrp", {}), qr_id=it.get("qr_id"))
        db.add(p)
        by_brand[p.brand] = p
    db.flush()
    for p in by_brand.values():
        for pack, price in (p.mrp or {}).items():
            db.add(models.Price(product_id=p.id, pack_size=pack, price=price, district=None, source="label"))
    counts["products"] = len(by_brand)

    bans = _read("state_crop_bans.json", seed_dir)
    n = 0
    for it in bans["items"]:
        for name in it["ai"]:
            db.add(models.StateCropBan(state=it["state"], crop=normalise.crop(it["crop"]),
                                       active_ingredient=get_ai(name),
                                       effective_from=date.fromisoformat(it["effective_from"]),
                                       source_url=it.get("source_url")))
            n += 1
    counts["state_crop_bans"] = n

    flags = _read("export_flags.json", seed_dir)
    for it in flags["items"]:
        db.add(models.ExportFlag(crop=normalise.crop(it["crop"]), market=it["market"],
                                 active_ingredient=get_ai(it["ai"]),
                                 note=it.get("note"), source_url=it.get("source_url")))
    counts["export_flags"] = len(flags["items"])
    db.flush()

    # Outputs of pipeline/parse_registry.py, when the official lists have been parsed.
    if (seed_dir / "registered_formulations.json").exists():
        n = 0
        for it in _read("registered_formulations.json", seed_dir)["items"]:
            f = _formulation(db, get_ai(it["ai"]), it["pct"], it["type"], registered=True,
                             source_file=it.get("source_file"), page=it.get("page"))
            f.registered = True
            if it.get("brand") and it["brand"] not in by_brand:
                p = models.Product(brand=it["brand"], company=it.get("company"), formulation=f,
                                   reg_no=it.get("reg_no"), pack_sizes=[], mrp={})
                db.add(p)
                by_brand[p.brand] = p
            n += 1
        counts["registered_formulations"] = n
    if (seed_dir / "banned_list.json").exists():
        n = 0
        for it in _read("banned_list.json", seed_dir)["items"]:
            ai = get_ai(it["name"])
            if it["status"] in ("banned", "withdrawn", "refused"):
                ai.banned = True
            elif it["status"] == "restricted":
                ai.restricted = True
            ai.ban_note = f"{it['status'].title()} (CIB&RC list, {it.get('source_file')}, page {it.get('page')})" + (
                f": {it['note']}" if it.get("note") else "")
            n += 1
        counts["banned_list"] = n
    db.flush()

    if demo_scans and (seed_dir / "demo_scans.json").exists():
        counts["demo_scans"] = _load_demo_scans(db, _read("demo_scans.json", seed_dir), by_brand)

    db.commit()
    from .rules import evaluate  # local imports: services import models
    from .services import radar, scan
    counts["batch_signals"] = radar.recompute(db)
    # Give every seeded scan the verdict the engine would have given it.
    for s in db.scalars(select(models.Scan).where(models.Scan.verdict.is_(None))):
        ident = scan.identify(db, product_id=s.product_id, fields={"batch": s.batch,
                              "exp_date": s.exp_date.isoformat() if s.exp_date else None})
        res = evaluate(scan.build_facts(db, ident, today=s.created_at.date()), "scan")
        s.verdict, s.fired_rules = res["verdict"], [r["id"] for r in res["fired"]]
    db.commit()
    return counts


def _load_demo_scans(db: Session, demo: dict, by_brand: dict[str, models.Product]) -> int:
    now = datetime.utcnow()
    centroids = demo["districts"]
    for s in demo["scans"]:
        p = by_brand[s["brand"]]
        lat, lon = centroids[s["district"]]
        db.add(models.Scan(
            user_hash=hashlib.sha256(f"demo-{s['district']}-{s['days_ago']}".encode()).hexdigest(),
            product_id=p.id, batch=s["batch"], mfg_date=date.fromisoformat(s["mfg"]),
            exp_date=date.fromisoformat(s["exp"]),
            qr_payload_hash=hashlib.sha256(s["qr"].encode()).hexdigest() if s.get("qr") else None,
            lat=lat, lon=lon, district=s["district"], shop=s.get("shop"),
            created_at=now - timedelta(days=s["days_ago"]), verdict=None, fired_rules=[],
            extracted={"seeded": True}))
    db.flush()
    for r in demo.get("reports", []):
        scan = db.scalar(select(models.Scan).where(models.Scan.batch == r["batch"]).limit(1))
        db.add(models.Report(scan_id=scan.id if scan else None, reason=r["reason"], status="open"))
    return len(demo["scans"])


def reset_and_seed(demo_scans: bool = True) -> dict:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        return load_all(db, demo_scans=demo_scans)


def ensure_seeded() -> None:
    """Create tables and load the seed once. Safe when several serverless instances start together:
    the loser of the race hits a unique-name conflict and simply uses the winner's data."""
    from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

    try:
        Base.metadata.create_all(engine)
    except (IntegrityError, OperationalError, ProgrammingError):
        pass  # another instance created the tables at the same moment
    with SessionLocal() as db:
        if db.scalar(select(models.ActiveIngredient).limit(1)) is not None:
            return
        try:
            load_all(db)
        except IntegrityError:
            db.rollback()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop and recreate all tables first")
    ap.add_argument("--no-demo-scans", action="store_true")
    a = ap.parse_args()
    if a.reset:
        print(reset_and_seed(demo_scans=not a.no_demo_scans))
    else:
        ensure_seeded()
        print("ok")
