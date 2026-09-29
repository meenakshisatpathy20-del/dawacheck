"""DawaCheck API (playbook section 11)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import config, i18n, models, normalise, schemas, seed
from .ai import explain as explain_mod
from .ai import extract, ocr
from .db import get_db
from .services import bill as bill_svc
from .services import catalogue, dose, mix, radar, scan, sos, spray, storage, weather


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed.ensure_seeded()
    yield


app = FastAPI(title="DawaCheck API", version="0.1.0", lifespan=lifespan,
              description="AI reads, rules decide: every verdict comes from the rules engine and cites its source.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _lang(lang: str | None) -> str:
    return lang if lang in i18n.LANGS else "en"


def _f(v: str | None) -> float | None:
    return float(v) if v not in (None, "") else None


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ok", "db": config.DATABASE_URL.split(":", 1)[0],
            "ocr": ocr.available(), "llm": extract.llm_enabled(), "offline": config.OFFLINE,
            "products": len(db.scalars(select(models.Product.id)).all()),
            "label_claims": len(db.scalars(select(models.LabelClaim.id)).all()),
            "scans": scan.count_scans(db)}


@app.post("/scan")
async def post_scan(
    image: UploadFile | None = File(None), qr_payload: str | None = Form(None), ocr_text: str | None = Form(None),
    product_id: int | None = Form(None), fields: str | None = Form(None, description="JSON of confirmed fields"),
    crop: str | None = Form(None), pest: str | None = Form(None), state: str | None = Form(None),
    lang: str = Form("en"), lat: str | None = Form(None), lon: str | None = Form(None),
    district: str | None = Form(None), shop: str | None = Form(None), user_id: str | None = Form(None),
    area_acre: str | None = Form(None), tank_l: str | None = Form(None), db: Session = Depends(get_db),
):
    data = await image.read() if image else None
    if not any([data, qr_payload, ocr_text, product_id, fields]):
        raise HTTPException(400, "Send an image, qr_payload, ocr_text, product_id or fields")
    return scan.scan(db, image=data, qr_payload=qr_payload, ocr_text=ocr_text, product_id=product_id,
                     fields=json.loads(fields) if fields else None, crop=crop, pest=pest, state=state,
                     lang=_lang(lang), lat=_f(lat), lon=_f(lon), district=district, shop=shop, user_id=user_id,
                     area_acre=_f(area_acre), tank_l=_f(tank_l))


@app.post("/bill")
async def post_bill(
    image: UploadFile | None = File(None), ocr_text: str | None = Form(None),
    items: str | None = Form(None, description="JSON list of {product_name, pack_size, quantity, price}"),
    crop: str | None = Form(None), pest: str | None = Form(None), state: str | None = Form(None),
    lang: str = Form("en"), district: str | None = Form(None), user_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    data = await image.read() if image else None
    parsed = [schemas.BillItem(**i).model_dump() for i in json.loads(items)] if items else None
    if not any([data, ocr_text, parsed]):
        raise HTTPException(400, "Send a bill image, ocr_text or items")
    return bill_svc.check_bill(db, image=data, ocr_text=ocr_text, items=parsed, crop=crop, pest=pest, state=state,
                               lang=_lang(lang), district=district, user_id=user_id)


@app.post("/mix-check")
def post_mix(req: schemas.MixRequest, db: Session = Depends(get_db)):
    res = mix.check(db, req.product_ids, _lang(req.lang))
    if res["status"] != "ok":
        raise HTTPException(404, res["message"])
    return res


@app.get("/claims")
def get_claims(product: int, crop: str | None = None, pest: str | None = None, db: Session = Depends(get_db)):
    p = catalogue.product_by_id(db, product)
    if p is None:
        raise HTTPException(404, "unknown product")
    claims = catalogue.claims_for(db, p.formulation)
    crop_c = normalise.claim_crop(crop)
    if crop_c:
        claims = [c for c in claims if c["crop"] == crop_c]
    if pest:
        claims = [c for c in claims if normalise.same_pest(c["pest"], pest)]
    return {"product": catalogue.product_card(p), "claims": claims}


@app.post("/dose")
def post_dose(req: schemas.DoseRequest, db: Session = Depends(get_db)):
    p = catalogue.product_by_id(db, req.product_id)
    if p is None:
        raise HTTPException(404, "unknown product")
    claim = catalogue.find_claim(db, p.formulation, req.crop, req.pest)
    if claim is None:
        raise HTTPException(422, "No label claim for this product on this crop and pest; see /scan for approved options")
    card = dose.compute(claim, req.area_acre, req.tank_l, p.formulation.type)
    if card.get("ok"):
        card["text"] = scan.dose_text(card, _lang(req.lang))
    return {"product": catalogue.product_card(p), "claim": claim, "dose": card}


@app.post("/spray-log")
def post_spray(req: schemas.SprayRequest, db: Session = Depends(get_db)):
    res = spray.log_spray(db, **{**req.model_dump(exclude={"lang"}), "lang": _lang(req.lang)})
    if res["status"] != "ok":
        raise HTTPException(404, res["message"])
    return res


@app.get("/passport/{plot_id}")
def get_passport(plot_id: str, db: Session = Depends(get_db)):
    p = spray.passport(db, plot_id)
    if p is None:
        raise HTTPException(404, "No sprays recorded for this plot")
    return p


@app.get("/rotation")
def get_rotation(plot_id: str, crop: str | None = None, pest: str | None = None, lang: str = "en",
                 db: Session = Depends(get_db)):
    return spray.rotation(db, plot_id, crop, pest, _lang(lang))


@app.get("/sos")
def get_sos(lat: float | None = None, lon: float | None = None, user_id: str | None = None,
            product_ids: str | None = Query(None, description="comma-separated"), lang: str = "en",
            db: Session = Depends(get_db)):
    ids = [int(x) for x in product_ids.split(",") if x.strip()] if product_ids else None
    return sos.sos(db, lat, lon, user_id, ids, _lang(lang))


@app.get("/weather-window")
def get_weather(lat: float | None = None, lon: float | None = None, lang: str = "en",
                demo: str | None = Query(None, pattern="^(rain|wind|clear)$")):
    return weather.window(lat, lon, _lang(lang), demo)


@app.post("/report")
async def post_report(reason: str = Form(...), scan_id: int | None = Form(None), photo: UploadFile | None = File(None),
                      db: Session = Depends(get_db)):
    url = storage.save_image(await photo.read(), "report")[1] if photo else None
    r = models.Report(scan_id=scan_id, reason=reason[:1000], photo_url=url)
    db.add(r)
    db.flush()
    radar.recompute(db)
    db.commit()
    return {"status": "ok", "report_id": r.id}


@app.get("/radar")
def get_radar(district: str | None = None, days: int = 90, db: Session = Depends(get_db)):
    return radar.dashboard(db, district, days)


@app.get("/radar/batch")
def get_radar_batch(batch: str, product_id: int | None = None, db: Session = Depends(get_db)):
    return radar.batch_detail(db, product_id, batch)


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    """Full catalogue for the app's offline cache and the product picker."""
    return [catalogue.product_card(p) for p in db.scalars(select(models.Product))]


@app.get("/crops")
def get_crops(db: Session = Depends(get_db)):
    rows = db.execute(select(models.LabelClaim.crop, models.LabelClaim.pest).distinct()).all()
    out: dict[str, set] = {}
    for crop, pest in rows:
        out.setdefault(crop, set()).add(pest)
    for child, parent in normalise._raw().get("crop_parents", {}).items():
        if parent in out:
            out[child] = set(out[parent])
    return {c: sorted(p) for c, p in sorted(out.items())}


@app.get("/offline-pack")
def get_offline_pack(crop: str | None = None, db: Session = Depends(get_db)):
    """Everything the app needs to give verdicts for cached products in airplane mode."""
    products = list(db.scalars(select(models.Product)))
    return {
        "products": [{**catalogue.product_card(p), "claims": catalogue.claims_for(db, p.formulation),
                      "banned": p.formulation.active_ingredient.banned or p.formulation.active_ingredient.restricted,
                      "registered": p.formulation.registered,
                      "state_bans": [{**b, "effective_from": str(b["effective_from"])}
                                     for b in catalogue.state_bans_for(db, p.formulation.active_ingredient)]}
                     for p in products],
        "i18n": {lg: i18n.table(lg) for lg in i18n.LANGS},
    }


@app.get("/i18n/{lang}")
def get_i18n(lang: str):
    return i18n.table(_lang(lang))


@app.post("/explain")
def post_explain(req: schemas.ExplainRequest):
    return explain_mod.explain(req.fired, _lang(req.lang))


config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

_DIST = Path(config.ROOT / "frontend" / "dist")
if _DIST.exists():
    app.mount("/app/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/app/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = _DIST / path
        return FileResponse(f if path and f.is_file() else _DIST / "index.html")
