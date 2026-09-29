"""C1-C6: scan -> identify -> registry + label-claim checks -> dose, PHI, safety."""
from __future__ import annotations

import hashlib
from datetime import date

from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config, i18n, models, normalise
from ..ai import extract, ocr, qr
from ..rules import evaluate
from . import catalogue, dose, radar, storage


def user_hash(user_id: str | None) -> str | None:
    if not user_id:
        return None
    return hashlib.sha256(f"{config.USER_HASH_SALT}:{user_id}".encode()).hexdigest()


def _best_line_match(db: Session, text: str):
    """Fuzzy-match every OCR line against catalogue brands; best (product, score) first."""
    brands = list(db.scalars(select(models.Product)))
    best: dict[int, tuple[models.Product, float]] = {}
    for line in [ln.strip() for ln in (text or "").splitlines() if len(ln.strip()) >= 3][:40]:
        for p in brands:
            s = fuzz.WRatio(line, p.brand)
            if s > best.get(p.id, (None, 0))[1]:
                best[p.id] = (p, s)
    return sorted(best.values(), key=lambda t: -t[1])[:3]


def identify(db: Session, *, product_id=None, qr_payload=None, ocr_text=None, fields=None, image=None,
             read_from_pack: bool = False) -> dict:
    """Turn whatever the farmer gave us into (product | ingredient + formulation) and extracted fields."""
    out = {"extracted": {}, "method": None, "candidates": [], "needs_confirmation": False,
           "product": None, "ai": None, "formulation": None, "ocr_unavailable": False,
           "field_checks": {}, "mismatch": []}
    lines: list[dict] = []
    ex: dict = {}
    if image and not qr_payload:
        qr_payload = qr.decode_image(image)
    if qr_payload:
        q = qr.parse_payload(qr_payload)
        ex.update({k: v for k, v in q.items() if k != "raw"})
        out["method"] = "qr"
        out["qr_hash"] = hashlib.sha256(qr_payload.encode()).hexdigest()
        out["qr_payload"] = qr_payload
    if image and not qr_payload and not ocr_text and not product_id:
        lines, engine = ocr.read_lines(image)
        out["ocr_engine"] = engine
        if engine is None:
            out["ocr_unavailable"] = True
        else:
            ocr_text = "\n".join(ln["text"] for ln in lines)
    if ocr_text:
        names = [a.name for a in catalogue.all_ingredients(db)]
        fields_x, method = extract.extract_label(ocr_text, names)
        for k, v in fields_x.items():
            if v is not None and k not in ex:
                ex[k] = v
        out["method"] = f"{out['method']}+ocr:{method}" if out["method"] else f"ocr:{method}"
    for k, v in (fields or {}).items():  # farmer-confirmed / manually typed values win
        if v not in (None, ""):
            ex[k] = v
    out["extracted"] = ex

    p = None
    if product_id:
        p = catalogue.product_by_id(db, int(product_id))
        out["method"] = out["method"] or ("confirmed+ocr" if read_from_pack else "confirmed")
    p = p or catalogue.product_by_qr(db, ex.get("qr_id")) or catalogue.product_by_reg(db, ex.get("reg_no"))
    if p is None and (ex.get("brand") or ex.get("active_ingredient") or ocr_text):
        cands = catalogue.match_products(db, ex.get("brand"), ex.get("active_ingredient"))
        if ocr_text:
            merged = {c[0].id: c for c in cands}
            for c in _best_line_match(db, ocr_text):
                if c[1] > merged.get(c[0].id, (None, 0))[1]:
                    merged[c[0].id] = c
            cands = sorted(merged.values(), key=lambda t: -t[1])[:3]
        out["candidates"] = [{**catalogue.product_card(c[0]), "score": round(c[1])} for c in cands]
        if cands and cands[0][1] >= catalogue.MATCH_THRESHOLD:
            p = cands[0][0]
            # Low margin between top two brands -> ask the farmer.
            out["needs_confirmation"] = len(cands) > 1 and cands[0][1] - cands[1][1] < 5
        elif cands:
            out["needs_confirmation"] = True
    out["product"] = p

    if p is not None:
        out["formulation"] = p.formulation
        out["ai"] = p.formulation.active_ingredient
        # Guardrail: the strength and form read from the pack must match the registered formulation.
        pct, ftype = ex.get("strength_pct"), ex.get("formulation")
        if pct not in (None, "") and abs(float(pct) - p.formulation.strength_pct) > 0.051:
            out["mismatch"].append("strength_pct")
        if ftype and str(ftype).upper() != p.formulation.type:
            out["mismatch"].append("formulation")
        if out["mismatch"]:
            out["needs_confirmation"] = True
    else:
        ai = catalogue.find_ai(db, ex.get("active_ingredient"))
        out["ai"] = ai
        if ai is not None:
            pct = ex.get("strength_pct")
            out["formulation"] = catalogue.find_formulation(db, ai, float(pct) if pct not in (None, "") else None,
                                                            ex.get("formulation"))
    if lines and image:
        out["field_checks"] = _field_checks(image, lines, ex)
        # Low-confidence fields do not block the verdict; the app asks the farmer to check them.
        out["check_fields"] = [k for k, fc in out["field_checks"].items() if fc["low"]]
    return out


CHECK_FIELDS = ("brand", "active_ingredient", "strength_pct", "batch", "mfg_date", "exp_date", "reg_no")


def _field_checks(image: bytes, lines: list[dict], ex: dict) -> dict:
    """Photo crop + OCR confidence for each field read from the pack."""
    out = {}
    for key, loc in ocr.locate_fields(lines, {k: ex.get(k) for k in CHECK_FIELDS}).items():
        crop = ocr.crop(image, loc["box"])
        url = storage.save_image(crop, "crops")[1] if crop else None
        out[key] = {"value": str(ex[key]), "conf": loc["conf"], "low": loc["conf"] < ocr.LOW_CONFIDENCE, "crop_url": url}
    return out


def build_facts(db: Session, ident: dict, crop=None, pest=None, state=None, today: date | None = None) -> dict:
    p, ai, f, ex = ident["product"], ident["ai"], ident["formulation"], ident["extracted"]
    attempted = bool(p or ex.get("active_ingredient") or ex.get("brand") or ex.get("reg_no") or ex.get("qr_id"))
    identified = {
        "attempted": attempted and not ident.get("needs_confirmation"),
        "ai_known": ai is not None,
        "ai_text": ex.get("active_ingredient") or ex.get("brand"),
        "formulation_registered": (f.registered if f is not None else (False if ai is not None and ex.get("strength_pct") else None)),
        "product_matched": p is not None,
        "reg_no_extracted": ex.get("reg_no"),
        "reg_no_catalogue": p.reg_no if p is not None else None,
    }
    if ai is not None and f is None and identified["formulation_registered"] is None:
        identified["attempted"] = False  # not enough on the label to judge; ask the farmer
    exp = extract.parse_date(str(ex["exp_date"]), end_of_month=True) if ex.get("exp_date") else None
    return {
        "today": today or date.today(),
        "identified": identified,
        "ai": catalogue.ai_dict(ai),
        "formulation_label": f.label if f is not None else None,
        "exp_date": exp,
        "crop": normalise.crop(crop), "claim_crop": normalise.claim_crop(crop),
        "pest": normalise.pest(pest), "state": (state or "").strip().lower() or None,
        "claims": catalogue.claims_for(db, f),
        "state_bans": catalogue.state_bans_for(db, ai),
        "batch_signal": radar.signal_for(db, p.id if p else None, ex.get("batch")),
        "read_from_pack": "ocr" in (ident.get("method") or ""),
        "extracted_keys": {k for k, v in ex.items() if v not in (None, "")},
    }


def render(fired: list[dict], lang: str) -> list[dict]:
    out = []
    for r in fired:
        out.append({**r, "message": i18n.render_rule(r, lang), "message_en": i18n.render_rule(r, "en")})
    return out


def safety_card(p: models.Product | None, ai: models.ActiveIngredient | None, lang: str) -> dict | None:
    if ai is None:
        return None
    colour = (catalogue.colour_of(p) if p else ai.toxicity_colour) or None
    return {
        "toxicity_colour": colour,
        "colour_meaning": i18n.t(f"colour.{colour}", lang) if colour else None,
        "gear": i18n.t(f"gear.{colour}", lang) if colour else None,
        "red_confirm": i18n.t("red_confirm", lang) if colour == "red" else None,
        "first_aid": ai.first_aid_text,
        "antidote_from_label": ai.antidote_text,
        "chem_class": ai.chem_class,
        "poison_helpline": "1800 116 117",
    }


def scan(db: Session, *, image: bytes | None = None, qr_payload: str | None = None, ocr_text: str | None = None,
         product_id: int | None = None, fields: dict | None = None, crop: str | None = None, pest: str | None = None,
         state: str | None = None, lang: str = "en", lat: float | None = None, lon: float | None = None,
         district: str | None = None, shop: str | None = None, user_id: str | None = None,
         area_acre: float | None = None, tank_l: float | None = None, log: bool = True,
         today: date | None = None, read_from_pack: bool = False) -> dict:
    image_hash = image_url = None
    if image:
        image_hash, image_url = storage.save_image(image, "pack")
    ident = identify(db, product_id=product_id, qr_payload=qr_payload, ocr_text=ocr_text, fields=fields, image=image,
                     read_from_pack=read_from_pack)
    p, ai, f, ex = ident["product"], ident["ai"], ident["formulation"], ident["extracted"]

    if ident["ocr_unavailable"] and not p and not ai:
        return {"status": "need_input", "reason": "ocr_unavailable",
                "message": "No text reader on the server. Scan the QR code, send on-device OCR text, or pick the product."}

    scan_row = None
    if log:
        scan_row = models.Scan(
            user_hash=user_hash(user_id), product_id=p.id if p else None, batch=ex.get("batch"),
            mfg_date=extract.parse_date(str(ex["mfg_date"])) if ex.get("mfg_date") else None,
            exp_date=extract.parse_date(str(ex["exp_date"]), end_of_month=True) if ex.get("exp_date") else None,
            qr_payload_hash=ident.get("qr_hash"), image_hash=image_hash, lat=lat, lon=lon,
            district=district, shop=shop, crop=normalise.crop(crop), pest=normalise.pest(pest),
            extracted={k: (str(v) if v is not None else None) for k, v in ex.items()})
        db.add(scan_row)
        db.flush()
        radar.recompute(db)  # the new scan may create a date-conflict or cloned-QR signal

    facts = build_facts(db, ident, crop, pest, state, today)
    result = evaluate(facts, "scan")
    fired = render(result["fired"], lang)
    verdict = result["verdict"]
    if ident["needs_confirmation"] and not fired:
        verdict = "grey"

    claim = catalogue.find_claim(db, f, crop, pest) if f is not None and crop else None
    dose_card = None
    if claim and area_acre:
        dose_card = dose.compute(claim, float(area_acre), float(tank_l or config.DEFAULT_TANK_L), f.type)
        if dose_card.get("ok"):
            dose_card["text"] = dose_text(dose_card, lang)
    phi = None
    if claim and claim.get("phi_days") is not None:
        safe = dose.safe_harvest_date(facts["today"], claim["phi_days"])
        phi = {"days": claim["phi_days"], "safe_from_if_sprayed_today": safe.isoformat(),
               "text": i18n.t("phi.safe_from", lang, date=safe.isoformat())}

    suggestions = []
    if crop and (verdict in ("yellow", "red") or any(r["id"] in ("R5", "R6") for r in fired)):
        state_banned = catalogue.state_banned_names(db, facts["state"], facts["crop"])
        suggestions = [o for o in catalogue.approved_for(db, crop, pest, limit=12)
                       if not (f is not None and o["formulation_id"] == f.id)
                       and o["active_ingredient"] not in state_banned][:6]
    headline = i18n.t(f"verdict.{verdict}", lang)
    speech = " ".join([headline] + [r["message"] for r in fired if r["verdict"] != "info"])
    if suggestions and any(r["id"] in ("R5", "R6") for r in fired):
        speech += " " + i18n.t("approved_options", lang, options=", ".join(o["formulation"] for o in suggestions[:3]))

    export = []
    if ai is not None and facts["claim_crop"]:
        rows = db.scalars(select(models.ExportFlag).where(models.ExportFlag.active_ingredient_id == ai.id,
                                                          models.ExportFlag.crop == facts["claim_crop"]))
        export = [{"market": e.market, "note": e.note, "source_url": e.source_url} for e in rows]

    if scan_row is not None:
        scan_row.verdict = verdict
        scan_row.fired_rules = [r["id"] for r in fired]
        db.commit()

    return {
        "status": "ok", "scan_id": scan_row.id if scan_row else None,
        "verdict": verdict, "headline": headline, "speech": speech, "tts_locale": i18n.TTS_LOCALE.get(lang, "en-IN"),
        "fired": fired, "product": catalogue.product_card(p) if p else None,
        "identified": {"active_ingredient": ai.name if ai else None, "formulation": f.label if f else None,
                       "method": ident["method"], "needs_confirmation": ident["needs_confirmation"],
                       "read_from_pack": facts["read_from_pack"], "ocr_engine": ident.get("ocr_engine")},
        "field_checks": ident["field_checks"], "check_fields": ident.get("check_fields", []),
        "mismatch": ident["mismatch"],
        "candidates": ident["candidates"], "extracted": {k: (str(v) if v is not None else None) for k, v in ex.items()},
        "claim": claim, "dose": dose_card, "phi": phi, "safety": safety_card(p, ai, lang),
        "suggestions": suggestions, "export_flags": export, "image_url": image_url,
        "data_note": _data_note(claim, facts["claims"]),
    }


def dose_text(card: dict, lang: str) -> str:
    params = {k: v for k, v in card.items() if k != "key"}
    params["area"] = f"{card['area_acre']:g}"
    if "tank_l" in params:
        params["tank_l"] = f"{card['tank_l']:g}"
    return i18n.t(card["key"], lang, **params)


def _data_note(claim: dict | None, claims: list[dict]) -> str | None:
    rows = [claim] if claim else claims
    if any(not c.get("verified") for c in rows):
        return "Label-claim data is sample data until replaced by the parsed CIB&RC Major Uses PDF."
    return None


def count_scans(db: Session) -> int:
    return db.scalar(select(func.count(models.Scan.id))) or 0
