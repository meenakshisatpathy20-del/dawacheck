"""C5 waiting period, W3 MRL Passport, W5 Resistance Rotation Planner."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import i18n, models, normalise
from ..rules import evaluate
from . import catalogue, dose, scan

PASSPORT_NOTE = ("Self-declared spray record plus a residue-risk estimate. It is not a lab certificate; "
                 "residue testing stays with the buyer or exporter.")


def _phi_for(db: Session, product: models.Product, crop: str, pest: str | None) -> tuple[int | None, dict | None]:
    """Waiting period from the label claim. If the pest is unknown, use the longest PHI on that crop (safe side)."""
    claim = catalogue.find_claim(db, product.formulation, crop, pest)
    if claim:
        return claim["phi_days"], claim
    crop_c = normalise.claim_crop(crop)
    rows = [c for c in catalogue.claims_for(db, product.formulation) if c["crop"] == crop_c and c["phi_days"] is not None]
    if not rows:
        return None, None
    c = max(rows, key=lambda r: r["phi_days"])
    return c["phi_days"], c


def log_spray(db: Session, *, plot_id: str, crop: str, product_id: int, spray_date: date, state: str | None = None,
              pest: str | None = None, area_acre: float | None = None, tanks: int | None = None,
              planned_harvest: date | None = None, user_id: str | None = None, lang: str = "en") -> dict:
    p = catalogue.product_by_id(db, product_id)
    if p is None:
        return {"status": "error", "message": "unknown product"}
    phi, claim = _phi_for(db, p, crop, pest)
    safe = dose.safe_harvest_date(spray_date, phi)
    row = models.SprayLog(user_hash=scan.user_hash(user_id), plot_id=plot_id, crop=normalise.crop(crop),
                          state=(state or "").lower() or None, pest=normalise.pest(pest), product_id=p.id,
                          spray_date=spray_date, area_acre=area_acre, tanks=tanks, safe_harvest_date=safe)
    db.add(row)
    db.commit()

    ai = p.formulation.active_ingredient
    facts = {"today": spray_date, "ai": catalogue.ai_dict(ai), "crop": normalise.crop(crop),
             "state": row.state, "state_bans": catalogue.state_bans_for(db, ai),
             "spray": {"spray_date": spray_date, "phi_days": phi, "planned_harvest": planned_harvest,
                       "source": {"file": claim["source_file"], "page": claim["page"]} if claim else None}}
    result = evaluate(facts, "spray")
    fired = scan.render(result["fired"], lang)
    plot_safe = plot_safe_date(db, plot_id)
    return {
        "status": "ok", "spray_id": row.id, "verdict": result["verdict"], "fired": fired,
        "phi_days": phi, "safe_harvest_date": safe.isoformat() if safe else None,
        "plot_safe_harvest_date": plot_safe.isoformat() if plot_safe else None,
        "text": i18n.t("phi.safe_from", lang, date=(plot_safe or safe).isoformat()) if (plot_safe or safe) else None,
        "reminder": {"date": (plot_safe or safe).isoformat(), "title": f"Safe to harvest {row.crop}"} if (plot_safe or safe) else None,
        "phi_unknown": phi is None, "rotation": rotation(db, plot_id, crop, pest, lang),
    }


def sprays(db: Session, plot_id: str) -> list[models.SprayLog]:
    return list(db.scalars(select(models.SprayLog).where(models.SprayLog.plot_id == plot_id)
                           .order_by(models.SprayLog.spray_date, models.SprayLog.id)))


def plot_safe_date(db: Session, plot_id: str) -> date | None:
    """Safe harvest date = latest (spray date + waiting period) across all sprays on the plot."""
    dates = [s.safe_harvest_date for s in sprays(db, plot_id) if s.safe_harvest_date]
    return max(dates) if dates else None


def passport(db: Session, plot_id: str) -> dict | None:
    rows = sprays(db, plot_id)
    if not rows:
        return None
    crop, state = rows[-1].crop, rows[-1].state
    out_rows, flags = [], []
    for s in rows:
        ai = s.product.formulation.active_ingredient
        f_rows = []
        banned = catalogue.state_banned_names(db, state, crop, on=s.spray_date)
        if ai.name in banned:
            f_rows.append({"type": "state_ban", "text": f"{ai.name} is banned for {crop} in {state.title()}"})
        for e in db.scalars(select(models.ExportFlag).where(models.ExportFlag.active_ingredient_id == ai.id,
                                                            models.ExportFlag.crop == normalise.claim_crop(crop))):
            f_rows.append({"type": "export", "market": e.market, "text": e.note, "source_url": e.source_url})
        if ai.banned or ai.restricted:
            f_rows.append({"type": "national_ban", "text": f"{ai.name} is {'banned' if ai.banned else 'restricted'} in India"})
        flags += f_rows
        out_rows.append({"date": s.spray_date.isoformat(), "product": s.product.brand,
                         "formulation": s.product.formulation.label, "active_ingredient": ai.name,
                         "area_acre": s.area_acre, "safe_harvest_date": s.safe_harvest_date.isoformat() if s.safe_harvest_date else None,
                         "flags": f_rows})
    safe = plot_safe_date(db, plot_id)
    risk = "high" if any(f["type"] in ("state_ban", "national_ban") for f in flags) else (
        "medium" if flags else "low")
    return {"plot_id": plot_id, "crop": crop, "state": state, "sprays": out_rows, "flags": flags,
            "safe_harvest_date": safe.isoformat() if safe else None,
            "safe_now": bool(safe and safe <= date.today()), "residue_risk": risk, "note": PASSPORT_NOTE}


def rotation(db: Session, plot_id: str, crop: str | None = None, pest: str | None = None, lang: str = "en") -> dict:
    rows = sprays(db, plot_id)
    history = []
    for s in rows:
        ai = s.product.formulation.active_ingredient
        history.append({"label": s.product.brand, "ai_name": ai.name, "group": ai.irac_frac_group,
                        "scheme": ai.moa_scheme, "date": s.spray_date.isoformat()})
    result = evaluate({"rotation": history}, "rotation")
    crop = crop or (rows[-1].crop if rows else None)
    pest = pest or (rows[-1].pest if rows else None)
    if result["fired"]:
        grp = result["fired"][0]["params"]["group"]
        state = rows[-1].state if rows else None
        banned = catalogue.state_banned_names(db, state, normalise.crop(crop))
        options = [o for o in catalogue.approved_for(db, crop, pest, exclude_groups={grp}, limit=12)
                   if o["active_ingredient"] not in banned][:5]
        return {"status": "change", "group": grp, "fired": scan.render(result["fired"], lang),
                "text": i18n.t("rotation.change", lang, group=grp), "options": options, "history": history}
    return {"status": "ok", "text": i18n.t("rotation.ok", lang) if len(history) >= 2 else None,
            "options": [], "history": history}
