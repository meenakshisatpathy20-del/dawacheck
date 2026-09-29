"""Admin screen API (playbook section 18): add a ban in minutes, review farmer-added products.

Rules change often (new state bans, QR rollout). Bans are rows with effective
dates, so a change takes effect without a code release. Every endpoint needs
the X-Admin-Token header; the router is disabled unless ADMIN_TOKEN is set.
"""
from __future__ import annotations

import hmac
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config, models, normalise
from .db import get_db
from .services import cache, catalogue, scan, storage


def require_admin(x_admin_token: str | None = Header(None)):
    if not config.ADMIN_TOKEN:
        raise HTTPException(503, "Admin is disabled: set ADMIN_TOKEN")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, config.ADMIN_TOKEN):
        raise HTTPException(401, "Wrong admin token")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
public = APIRouter(tags=["catalogue"])


def _ai(db: Session, name: str) -> models.ActiveIngredient:
    key = normalise.ingredient(name)
    ai = catalogue.find_ai(db, key)
    if ai is None:
        ai = models.ActiveIngredient(name=key)
        db.add(ai)
        db.flush()
    return ai


class StateBanIn(BaseModel):
    state: str = Field(min_length=2)
    crop: str = Field(min_length=2)
    active_ingredient: str = Field(min_length=2)
    effective_from: date
    source_url: str = Field(min_length=8, description="State order or notification")


class NationalStatusIn(BaseModel):
    banned: bool = False
    restricted: bool = False
    banned_from: date | None = None
    ban_note: str | None = None
    source_url: str = Field(min_length=8)


class ApproveIn(BaseModel):
    brand: str | None = None
    active_ingredient: str | None = None
    strength_pct: float | None = None
    formulation: str | None = None
    reg_no: str | None = None
    company: str | None = None
    toxicity_colour: str | None = Field(None, pattern="^(red|yellow|blue|green)$")
    note: str | None = None


def _ban_row(b: models.StateCropBan) -> dict:
    return {"id": b.id, "state": b.state, "crop": b.crop, "active_ingredient": b.active_ingredient.name,
            "effective_from": b.effective_from.isoformat() if b.effective_from else None, "source_url": b.source_url}


@router.get("/bans")
def list_bans(db: Session = Depends(get_db)):
    national = [{"name": a.name, "banned": a.banned, "restricted": a.restricted, "ban_note": a.ban_note,
                 "banned_from": a.banned_from.isoformat() if a.banned_from else None, "source_url": a.source_url}
                for a in db.scalars(select(models.ActiveIngredient)) if a.banned or a.restricted]
    return {"state": [_ban_row(b) for b in db.scalars(select(models.StateCropBan))], "national": national}


@router.post("/state-bans")
def add_state_ban(req: StateBanIn, db: Session = Depends(get_db)):
    b = models.StateCropBan(state=req.state.strip().lower(), crop=normalise.crop(req.crop),
                            active_ingredient=_ai(db, req.active_ingredient), effective_from=req.effective_from,
                            source_url=req.source_url)
    db.add(b)
    db.commit()
    cache.clear()
    return _ban_row(b)


@router.delete("/state-bans/{ban_id}")
def delete_state_ban(ban_id: int, db: Session = Depends(get_db)):
    b = db.get(models.StateCropBan, ban_id)
    if b is None:
        raise HTTPException(404, "no such ban")
    db.delete(b)
    db.commit()
    cache.clear()
    return {"status": "deleted"}


@router.put("/ingredients/{name}")
def set_national_status(name: str, req: NationalStatusIn, db: Session = Depends(get_db)):
    ai = _ai(db, name)
    ai.banned, ai.restricted, ai.banned_from = req.banned, req.restricted, req.banned_from
    ai.ban_note, ai.source_url = req.ban_note, req.source_url
    db.commit()
    cache.clear()
    return catalogue.ai_dict(ai)


def _submission(s: models.ProductSubmission) -> dict:
    return {"id": s.id, "brand": s.brand, "active_ingredient": s.active_ingredient, "strength_pct": s.strength_pct,
            "formulation": s.formulation, "reg_no": s.reg_no, "company": s.company,
            "toxicity_colour": s.toxicity_colour, "photo_url": s.photo_url, "status": s.status,
            "review_note": s.review_note, "product_id": s.product_id, "created_at": s.created_at.isoformat()}


@router.get("/submissions")
def list_submissions(status: str = "pending", db: Session = Depends(get_db)):
    q = select(models.ProductSubmission).order_by(models.ProductSubmission.created_at.desc())
    if status != "all":
        q = q.where(models.ProductSubmission.status == status)
    return [_submission(s) for s in db.scalars(q)]


@router.post("/submissions/{sid}/approve")
def approve(sid: int, req: ApproveIn, db: Session = Depends(get_db)):
    s = db.get(models.ProductSubmission, sid)
    if s is None or s.status != "pending":
        raise HTTPException(404, "no pending submission with this id")
    for k, v in req.model_dump(exclude={"note"}).items():
        if v not in (None, ""):
            setattr(s, k, v)
    if not (s.active_ingredient and s.strength_pct and s.formulation):
        raise HTTPException(422, "Chemical, strength and formulation are needed to add the product")
    ai = _ai(db, s.active_ingredient)
    f = catalogue.find_formulation(db, ai, s.strength_pct, s.formulation)
    if f is None:
        # Not in the registered formulations we know: the product is added but R1 will still flag it.
        f = models.Formulation(active_ingredient=ai, strength_pct=float(s.strength_pct), type=s.formulation.upper(),
                               registered=False, source_file="farmer submission; not in parsed registry")
        db.add(f)
        db.flush()
    p = models.Product(brand=s.brand, company=s.company, formulation=f, reg_no=s.reg_no,
                       toxicity_colour=s.toxicity_colour, label_image_url=s.photo_url, pack_sizes=[], mrp={})
    db.add(p)
    db.flush()
    s.status, s.product_id, s.review_note = "approved", p.id, req.note
    db.commit()
    cache.clear()
    return {**_submission(s), "product": catalogue.product_card(p)}


@router.post("/submissions/{sid}/reject")
def reject(sid: int, note: str = Form(""), db: Session = Depends(get_db)):
    s = db.get(models.ProductSubmission, sid)
    if s is None or s.status != "pending":
        raise HTTPException(404, "no pending submission with this id")
    s.status, s.review_note = "rejected", note or None
    db.commit()
    return _submission(s)


@router.put("/reports/{report_id}")
def set_report_status(report_id: int, status: str = Form(..., pattern="^(open|confirmed|dismissed)$"),
                      db: Session = Depends(get_db)):
    """An officer confirms or dismisses a farmer report after inspection (impact metric)."""
    r = db.get(models.Report, report_id)
    if r is None:
        raise HTTPException(404, "no such report")
    r.status = status
    db.commit()
    return {"id": r.id, "status": r.status}


@public.post("/products/submit")
async def submit_product(
    brand: str = Form(..., min_length=2), active_ingredient: str | None = Form(None),
    strength_pct: float | None = Form(None), formulation: str | None = Form(None), reg_no: str | None = Form(None),
    company: str | None = Form(None), user_id: str | None = Form(None), photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """Farmer adds a product the app did not know. Nothing reaches the catalogue until an admin approves it."""
    url = storage.save_image(await photo.read(), "submissions")[1] if photo else None
    s = models.ProductSubmission(brand=brand[:120], active_ingredient=active_ingredient, strength_pct=strength_pct,
                                 formulation=(formulation or "").upper() or None, reg_no=reg_no, company=company,
                                 photo_url=url, user_hash=scan.user_hash(user_id))
    db.add(s)
    db.commit()
    return {"status": "pending", "submission_id": s.id}


__all__ = ["router", "public"]
