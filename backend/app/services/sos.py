"""W4 Doctor Card + Poison SOS. Repeats label text and routes to professionals;
never gives treatment advice of its own."""
from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config, i18n, models
from . import catalogue, radar, scan

NPIC = {"name": "AIIMS National Poisons Information Centre", "phone": "1800 116 117", "tel": "18001161117",
        "url": "https://www.aiims.edu/"}
AMBULANCE = {"name": "Ambulance", "phone": "108", "tel": "108"}


def nearest_health_centres(lat: float | None, lon: float | None, limit: int = 3) -> list[dict]:
    """OpenStreetMap (Overpass) lookup. Empty when offline; the app then shows 108."""
    if lat is None or lon is None or config.OFFLINE:
        return []
    q = f"""[out:json][timeout:8];
    (node(around:15000,{lat},{lon})[amenity~"hospital|clinic|doctors"];
     way(around:15000,{lat},{lon})[amenity~"hospital|clinic"];);
    out center 30;"""
    try:
        r = httpx.post(config.OVERPASS_URL, data={"data": q}, timeout=10)
        r.raise_for_status()
        els = r.json().get("elements", [])
    except (httpx.HTTPError, ValueError):
        return []
    out = []
    for e in els:
        la = e.get("lat") or e.get("center", {}).get("lat")
        lo = e.get("lon") or e.get("center", {}).get("lon")
        if la is None:
            continue
        tags = e.get("tags", {})
        out.append({"name": tags.get("name") or tags.get("amenity", "Health centre").title(),
                    "type": tags.get("amenity"), "phone": tags.get("phone"), "lat": la, "lon": lo,
                    "km": round(radar.haversine_km((lat, lon), (la, lo)), 1)})
    return sorted(out, key=lambda x: x["km"])[:limit]


def doctor_card(db: Session, user_id: str | None = None, product_ids: list[int] | None = None) -> list[dict]:
    """Auto-filled from the farmer's last sprays and scans (or the given products)."""
    entries: list[tuple[models.Product, str | None]] = []
    if product_ids:
        entries = [(catalogue.product_by_id(db, i), None) for i in product_ids]
    elif user_id:
        h = scan.user_hash(user_id)
        for s in db.scalars(select(models.SprayLog).where(models.SprayLog.user_hash == h)
                            .order_by(models.SprayLog.spray_date.desc(), models.SprayLog.created_at.desc()).limit(3)):
            # Date sprayed, plus the time it was logged in the app (logged right after spraying).
            when = s.spray_date.isoformat()
            if s.created_at and s.created_at.date() == s.spray_date:
                when += f" {s.created_at.strftime('%H:%M')} UTC"
            entries.append((s.product, when))
        for s in db.scalars(select(models.Scan).where(models.Scan.user_hash == h, models.Scan.product_id.is_not(None))
                            .order_by(models.Scan.created_at.desc()).limit(3)):
            entries.append((db.get(models.Product, s.product_id), None))
    seen, cards = set(), []
    for p, sprayed in entries:
        if p is None or p.id in seen:
            continue
        seen.add(p.id)
        ai = p.formulation.active_ingredient
        cards.append({"product": p.brand, "active_ingredient": ai.name, "strength": p.formulation.label,
                      "chem_class": ai.chem_class, "moa_group": ai.irac_frac_group,
                      "label_colour": catalogue.colour_of(p),
                      "antidote_from_label": ai.antidote_text, "first_aid_from_label": ai.first_aid_text,
                      "last_spray": sprayed})
    return cards


def sos(db: Session, lat=None, lon=None, user_id=None, product_ids=None, lang: str = "en") -> dict:
    cards = doctor_card(db, user_id, product_ids)
    first_aid = cards[0]["first_aid_from_label"] if cards else None
    if not first_aid:
        ai = db.scalar(select(models.ActiveIngredient).limit(1))
        first_aid = ai.first_aid_text if ai else None
    label_keys = ["title", "exposure", "product", "ai", "class", "colour", "antidote", "last_spray", "none", "npic"]
    return {
        "helplines": [NPIC, AMBULANCE],
        # Doctor Card is shown in English (for the doctor) and the farmer's language side by side.
        "labels": {lg: {k: i18n.t(f"doctor.{k}", lg) for k in label_keys} for lg in dict.fromkeys(["en", lang])},
        "colour_names": {lg: {c: i18n.t(f"colour.{c}", lg) for c in ("red", "yellow", "blue", "green")}
                         for lg in dict.fromkeys(["en", lang])},
        "say": [i18n.t("sos.call", lang), i18n.t("sos.ambulance", lang)],
        "first_aid": first_aid,
        "doctor_card": cards,
        "health_centres": nearest_health_centres(lat, lon),
        "disclaimer": i18n.t("sos.no_advice", lang),
        "tts_locale": i18n.TTS_LOCALE.get(lang, "en-IN"),
    }
