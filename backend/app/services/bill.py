"""W1 Bill Scan: check every product on a dealer's bill and show cheaper same-chemical options."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import i18n, models
from ..ai import extract, ocr
from . import catalogue, scan, storage

UNIT = {"ml": 1, "l": 1000, "ltr": 1000, "litre": 1000, "g": 1, "gm": 1, "kg": 1000}


def pack_base(pack: str | None) -> float | None:
    """'250 ml' -> 250 ; '1 L' -> 1000 ; '5 kg' -> 5000 (ml or g)."""
    if not pack:
        return None
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", pack)
    if not m or m.group(2).lower() not in UNIT:
        return None
    return float(m.group(1)) * UNIT[m.group(2).lower()]


def cheapest_same_chemical(db: Session, product: models.Product, district: str | None = None) -> dict | None:
    """Lowest price per ml/g among registered products with the same formulation."""
    same = list(db.scalars(select(models.Product).where(models.Product.formulation_id == product.formulation_id)))
    best = None
    for p in same:
        for pr in db.scalars(select(models.Price).where(models.Price.product_id == p.id)):
            base = pack_base(pr.pack_size)
            if not base:
                continue
            unit_price = pr.price / base
            local = district is not None and pr.district == district
            if best is None or unit_price < best["unit_price"]:
                best = {"product_id": p.id, "brand": p.brand, "pack_size": pr.pack_size, "price": pr.price,
                        "unit_price": unit_price, "seen": "near you" if local else "on the label MRP"}
    return best


def check_bill(db: Session, *, image: bytes | None = None, ocr_text: str | None = None, items: list[dict] | None = None,
               crop: str | None = None, pest: str | None = None, state: str | None = None, lang: str = "en",
               district: str | None = None, user_id: str | None = None) -> dict:
    method = "confirmed"
    if image:
        storage.save_image(image, "bill")
        if not ocr_text and not items:
            ocr_text, _ = ocr.read_text(image)
            if ocr_text is None:
                return {"status": "need_input", "reason": "ocr_unavailable",
                        "message": "No text reader on the server. Send on-device OCR text or type the items."}
    bill_total = None
    if items is None:
        parsed, method = extract.extract_bill(ocr_text or "")
        items, bill_total = parsed["items"], parsed.get("total")

    lines, bad, saving_total, total = [], 0, 0.0, 0.0
    for it in items:
        name = it.get("product_name") or ""
        price = it.get("price")
        qty = it.get("quantity") or 1
        total += float(price or 0)
        cands = catalogue.match_products(db, name)
        product = cands[0][0] if cands and cands[0][1] >= catalogue.MATCH_THRESHOLD else None
        line = {"input": it, "candidates": [{"id": c[0].id, "brand": c[0].brand, "score": round(c[1])} for c in cands],
                "needs_confirmation": product is None or (len(cands) > 1 and cands[0][1] - cands[1][1] < 5)}
        if product is None:
            line.update({"verdict": "grey", "message": i18n.t("verdict.grey", lang)})
            lines.append(line)
            continue
        res = scan.scan(db, product_id=product.id, crop=crop, pest=pest, state=state, lang=lang,
                        district=district, user_id=user_id, log=True)
        line.update({"product": res["product"], "verdict": res["verdict"], "fired": res["fired"],
                     "suggestions": res["suggestions"][:3]})
        if res["verdict"] in ("yellow", "red"):
            bad += 1
        base = pack_base(it.get("pack_size"))
        if price and base:
            unit_paid = float(price) / (base * float(qty))
            db.add(models.Price(product_id=product.id, pack_size=it["pack_size"], price=float(price) / float(qty),
                                district=district, source="bill"))
            best = cheapest_same_chemical(db, product, district)
            if best and best["product_id"] != product.id and best["unit_price"] < unit_paid * 0.98:
                saving = round((unit_paid - best["unit_price"]) * base * float(qty))
                if saving > 0:
                    saving_total += saving
                    line["cheaper"] = {**best, "saving": saving, "text": i18n.t("cheaper", lang, saving=saving)}
        lines.append(line)
    db.commit()

    total = bill_total or total
    crop_name = crop or ""
    summary = i18n.t("bill.summary", lang, total=f"{total:,.0f}", bad=bad, crop=crop_name)
    if saving_total:
        summary += " " + i18n.t("cheaper", lang, saving=f"{saving_total:,.0f}")
    worst = max((ln["verdict"] for ln in lines), key=lambda v: {"red": 4, "yellow": 3, "grey": 2}.get(v, 0), default="green")
    return {"status": "ok", "method": method, "items": lines, "total": total, "not_ok": bad,
            "saving": saving_total, "verdict": worst, "summary": summary,
            "tts_locale": i18n.TTS_LOCALE.get(lang, "en-IN"),
            "price_note": "Prices are those seen on labels and bills near you, not an official rate."}
