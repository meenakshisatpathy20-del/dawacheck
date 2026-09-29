"""Knowledge-base lookups: ingredients, formulations, products, label claims."""
from __future__ import annotations

from datetime import date

from rapidfuzz import fuzz, process, utils
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, normalise
from . import cache

MATCH_THRESHOLD = 85  # below this the farmer must confirm (playbook section 10)


def all_ingredients(db: Session) -> list[models.ActiveIngredient]:
    return list(db.scalars(select(models.ActiveIngredient)))


def find_ai(db: Session, text: str | None) -> models.ActiveIngredient | None:
    if not text:
        return None
    name = normalise.ingredient(text)
    ai = db.scalar(select(models.ActiveIngredient).where(models.ActiveIngredient.name == name))
    if ai:
        return ai
    choices = {}
    for a in all_ingredients(db):
        choices[a.name] = a
        for s in a.synonyms or []:
            choices[s.lower()] = a
    hit = process.extractOne(name, list(choices), scorer=fuzz.WRatio, processor=utils.default_process)
    return choices[hit[0]] if hit and hit[1] >= 88 else None


def find_formulation(db: Session, ai: models.ActiveIngredient, pct: float | None, ftype: str | None):
    q = select(models.Formulation).where(models.Formulation.active_ingredient_id == ai.id)
    rows = list(db.scalars(q))
    if pct is not None:
        rows = [f for f in rows if abs(f.strength_pct - float(pct)) < 0.051]
    if ftype:
        rows = [f for f in rows if f.type == ftype.upper()]
    return rows[0] if len(rows) == 1 or (rows and pct is not None and ftype) else None


def product_by_id(db: Session, pid: int) -> models.Product | None:
    return db.get(models.Product, pid)


def product_by_qr(db: Session, qr_id: str | None):
    return db.scalar(select(models.Product).where(models.Product.qr_id == qr_id)) if qr_id else None


def product_by_reg(db: Session, reg_no: str | None):
    if not reg_no:
        return None
    norm = "".join(ch for ch in reg_no.upper() if ch.isalnum())
    for p in db.scalars(select(models.Product).where(models.Product.reg_no.is_not(None))):
        if "".join(ch for ch in p.reg_no.upper() if ch.isalnum()) == norm:
            return p
    return None


def match_products(db: Session, brand: str | None, ai_text: str | None = None, limit: int = 3):
    """Fuzzy brand match (rapidfuzz). Returns [(product, score)] best first."""
    if not brand and not ai_text:
        return []
    products = list(db.scalars(select(models.Product).options(
        selectinload(models.Product.formulation).selectinload(models.Formulation.active_ingredient))))
    ai = normalise.ingredient(ai_text) if ai_text else None
    scored = []
    for p in products:
        s = fuzz.WRatio(brand, p.brand, processor=utils.default_process) if brand else 0  # case-insensitive
        if ai and p.formulation.active_ingredient.name == ai:
            s = min(100, s + 10) if brand else 70
        scored.append((p, s))
    scored.sort(key=lambda t: -t[1])
    return [t for t in scored[:limit] if t[1] >= 50]


def claim_dict(c: models.LabelClaim) -> dict:
    return {
        "id": c.id, "crop": c.crop, "pest": c.pest,
        "dose_ai_g_ha": [c.dose_ai_g_ha_min, c.dose_ai_g_ha_max],
        "dose_form_ha": [c.dose_form_ha_min, c.dose_form_ha_max], "unit": c.unit,
        "water_l_ha": c.water_l_ha, "phi_days": c.phi_days,
        "source_file": c.source_file, "page": c.page, "verified": c.verified,
    }


def claims_for(db: Session, formulation: models.Formulation | None) -> list[dict]:
    if formulation is None:
        return []
    key = f"claims:{formulation.id}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    rows = db.scalars(select(models.LabelClaim).where(models.LabelClaim.formulation_id == formulation.id))
    out = [claim_dict(c) for c in rows]
    cache.set(key, out)
    return out


def find_claim(db: Session, formulation, crop: str | None, pest: str | None) -> dict | None:
    crop_c = normalise.claim_crop(crop)
    rows = [c for c in claims_for(db, formulation) if c["crop"] == crop_c]
    if pest:
        rows = [c for c in rows if normalise.same_pest(c["pest"], pest)]
    return rows[0] if rows else None


def colour_of(p: models.Product) -> str | None:
    return p.toxicity_colour or p.formulation.active_ingredient.toxicity_colour


def product_card(p: models.Product) -> dict:
    f = p.formulation
    ai = f.active_ingredient
    return {
        "id": p.id, "brand": p.brand, "company": p.company, "reg_no": p.reg_no,
        "formulation": f.label, "formulation_id": f.id, "active_ingredient": ai.name,
        "strength_pct": f.strength_pct, "form_type": f.type,
        "chem_class": ai.chem_class, "kind": ai.kind, "moa_group": ai.irac_frac_group, "moa_scheme": ai.moa_scheme,
        "toxicity_colour": colour_of(p), "pack_sizes": p.pack_sizes, "mrp": p.mrp,
        "label_image_url": p.label_image_url,
    }


def approved_for(db: Session, crop: str | None, pest: str | None, exclude_groups: set[str] | None = None,
                 limit: int = 6) -> list[dict]:
    """Registered, non-banned formulations with a label claim for crop x pest."""
    crop_c = normalise.claim_crop(crop)
    if not crop_c:
        return []
    rows = db.scalars(select(models.LabelClaim).where(models.LabelClaim.crop == crop_c).options(
        selectinload(models.LabelClaim.formulation).selectinload(models.Formulation.active_ingredient)))
    out, seen = [], set()
    for c in rows:
        if pest and not normalise.same_pest(c.pest, pest):
            continue
        f = c.formulation
        ai = f.active_ingredient
        if not f.registered or ai.banned or ai.restricted or f.id in seen:
            continue
        if exclude_groups and ai.irac_frac_group in exclude_groups:
            continue
        seen.add(f.id)
        prods = list(db.scalars(select(models.Product).where(models.Product.formulation_id == f.id)))
        out.append({
            "formulation": f.label, "formulation_id": f.id, "active_ingredient": ai.name,
            "moa_group": ai.irac_frac_group, "moa_scheme": ai.moa_scheme,
            "claim": claim_dict(c), "products": [{"id": p.id, "brand": p.brand} for p in prods],
        })
    out.sort(key=lambda o: (o["claim"]["phi_days"] is None, o["claim"]["phi_days"] or 0))
    return out[:limit]


def state_bans_for(db: Session, ai: models.ActiveIngredient | None) -> list[dict]:
    if ai is None:
        return []
    rows = db.scalars(select(models.StateCropBan).where(models.StateCropBan.active_ingredient_id == ai.id))
    return [{"state": b.state, "crop": b.crop, "effective_from": b.effective_from, "source_url": b.source_url} for b in rows]


def state_banned_names(db: Session, state: str | None, crop: str | None, on: date | None = None) -> set[str]:
    if not state or not crop:
        return set()
    on = on or date.today()
    rows = db.scalars(select(models.StateCropBan).where(models.StateCropBan.state == state,
                                                        models.StateCropBan.crop == crop))
    return {b.active_ingredient.name for b in rows if b.effective_from is None or b.effective_from <= on}


def ai_dict(ai: models.ActiveIngredient | None) -> dict | None:
    if ai is None:
        return None
    return {"name": ai.name, "banned": ai.banned, "restricted": ai.restricted, "ban_note": ai.ban_note,
            "banned_from": ai.banned_from,
            "source_url": ai.source_url, "group": ai.irac_frac_group, "scheme": ai.moa_scheme,
            "toxicity_colour": ai.toxicity_colour, "chem_class": ai.chem_class}


def mix_item(p: models.Product) -> dict:
    ai = p.formulation.active_ingredient
    return {"product_id": p.id, "label": p.brand, "ai_name": ai.name, "group": ai.irac_frac_group,
            "scheme": ai.moa_scheme, "colour": colour_of(p), "form_type": p.formulation.type,
            "formulation": p.formulation.label}


def today() -> date:
    return date.today()
