"""DawaCheck API (playbook section 11)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import admin, config, geo, i18n, jobs, models, normalise, schemas, seed
from .ai import explain as explain_mod
from .ai import extract, ocr
from .db import get_db
from .services import bill as bill_svc
from .services import catalogue, dose, mix, radar, scan, sos, spray, storage, weather


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed.ensure_seeded()
    geo.init()
    yield


class ApiPrefix:
    """Serve every route both at /scan and at /api/scan.

    On Vercel the backend service is mounted under /api and the frontend calls /api/...;
    whether the platform forwards the prefix or strips it, the request reaches the same route.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path == "/api" or path.startswith("/api/"):
                new = path[4:] or "/"
                scope = {**scope, "path": new, "raw_path": new.encode(), "root_path": "/api"}  # links (e.g. /docs) keep the prefix
        await self.inner(scope, receive, send)


app = FastAPI(title="DawaCheck API", version="0.1.0", lifespan=lifespan,
              description="AI reads, rules decide: every verdict comes from the rules engine and cites its source.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(ApiPrefix)

if config.SERVERLESS:
    # Serverless platforms may not run ASGI lifespan events: prepare the database on cold start.
    seed.ensure_seeded()
    geo.init()
app.include_router(admin.router)
app.include_router(admin.public)


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
            "scans": scan.count_scans(db), "warnings": _warnings()}


def _warnings() -> list[str]:
    w = []
    if config.SERVERLESS and config.DATABASE_URL.startswith("sqlite"):
        w.append("Temporary SQLite in /tmp: scans, sprays and reports are lost between requests. "
                 "Attach Postgres (Vercel Storage > Neon) and redeploy.")
    if not ocr.available() and not extract.llm_enabled():
        w.append("No server-side label reader: set ANTHROPIC_API_KEY (photos are read on the phone until then).")
    return w


@app.post("/scan")
async def post_scan(
    image: UploadFile | None = File(None), qr_payload: str | None = Form(None), ocr_text: str | None = Form(None),
    product_id: int | None = Form(None), fields: str | None = Form(None, description="JSON of confirmed fields"),
    crop: str | None = Form(None), pest: str | None = Form(None), state: str | None = Form(None),
    lang: str = Form("en"), lat: str | None = Form(None), lon: str | None = Form(None),
    district: str | None = Form(None), shop: str | None = Form(None), user_id: str | None = Form(None),
    area_acre: str | None = Form(None), tank_l: str | None = Form(None),
    read_from_pack: bool = Form(False, description="true when re-checking after a label photo"),
    db: Session = Depends(get_db),
):
    data = await image.read() if image else None
    if not any([data, qr_payload, ocr_text, product_id, fields]):
        raise HTTPException(400, "Send an image, qr_payload, ocr_text, product_id or fields")
    return scan.scan(db, image=data, qr_payload=qr_payload, ocr_text=ocr_text, product_id=product_id,
                     fields=json.loads(fields) if fields else None, crop=crop, pest=pest, state=state,
                     lang=_lang(lang), lat=_f(lat), lon=_f(lon), district=district, shop=shop, user_id=user_id,
                     area_acre=_f(area_acre), tank_l=_f(tank_l), read_from_pack=read_from_pack)


@app.post("/scan/async")
async def post_scan_async(
    image: UploadFile = File(...), crop: str | None = Form(None), pest: str | None = Form(None),
    state: str | None = Form(None), lang: str = Form("en"), lat: str | None = Form(None), lon: str | None = Form(None),
    district: str | None = Form(None), shop: str | None = Form(None), user_id: str | None = Form(None),
    area_acre: str | None = Form(None), tank_l: str | None = Form(None),
):
    """Queue a slow label-photo OCR scan; poll GET /jobs/{job_id}."""
    kwargs = {"image": await image.read(), "crop": crop, "pest": pest, "state": state, "lang": _lang(lang),
              "lat": _f(lat), "lon": _f(lon), "district": district, "shop": shop, "user_id": user_id,
              "area_acre": _f(area_acre), "tank_l": _f(tank_l)}
    return jobs.submit("scan", kwargs)


@app.post("/jobs/run")
async def run_job(request: Request):
    """Called by Upstash QStash (signed) to run a queued job in its own function call."""
    body = await request.body()
    if not jobs.verify_qstash(request.headers.get("upstash-signature"), body):
        raise HTTPException(401, "bad signature")
    try:
        job_id = json.loads(body)["job_id"]
    except Exception:
        raise HTTPException(400, "job_id missing")
    out = jobs.run_stored(str(job_id))
    if out is None:
        raise HTTPException(404, "unknown job")
    return out


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    st = jobs.status(job_id)
    if st is None:
        raise HTTPException(404, "unknown job")
    return st


@app.get("/reminder.ics")
def get_reminder(plot_id: str, db: Session = Depends(get_db)):
    """Calendar reminder for the plot's safe harvest date (adds to the phone's calendar)."""
    safe = spray.plot_safe_date(db, plot_id)
    if safe is None:
        raise HTTPException(404, "No waiting period known for this plot")
    rows = spray.sprays(db, plot_id)
    crop = rows[-1].crop if rows else ""
    stamp = safe.strftime("%Y%m%d")
    ics = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DawaCheck//Spray reminder//EN", "BEGIN:VEVENT",
        f"UID:dawacheck-{plot_id}-{stamp}@dawacheck", f"DTSTAMP:{stamp}T000000Z",
        f"DTSTART;VALUE=DATE:{stamp}", f"SUMMARY:Safe to harvest {crop} (plot {plot_id})",
        "DESCRIPTION:Waiting period after the last spray is over. From DawaCheck.",
        "BEGIN:VALARM", "TRIGGER:PT8H", "ACTION:DISPLAY", "DESCRIPTION:Safe to harvest today", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR", ""])
    return Response(ics, media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="dawacheck-{plot_id}.ics"'})


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
def get_passport(plot_id: str, view: bool = False, db: Session = Depends(get_db)):
    """view=true is sent by the public passport page (a buyer opened it), not by the farmer's app."""
    p = spray.passport(db, plot_id)
    if p is None:
        raise HTTPException(404, "No sprays recorded for this plot")
    if view:
        db.add(models.PassportView(plot_id=plot_id))
        db.commit()
    return p


@app.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Impact metrics (playbook section 17)."""
    from sqlalchemy import func
    scans_n = db.scalar(select(func.count(models.Scan.id))) or 0
    by_verdict = dict(db.execute(select(models.Scan.verdict, func.count(models.Scan.id)).group_by(models.Scan.verdict)).all())
    bills = db.execute(select(func.count(models.BillCheck.id), func.coalesce(func.sum(models.BillCheck.saving), 0),
                              func.count(func.distinct(models.BillCheck.user_hash)))).one()
    sprays_n = db.scalar(select(func.count(models.SprayLog.id))) or 0
    sprays_safe = db.scalar(select(func.count(models.SprayLog.id)).where(models.SprayLog.safe_harvest_date.is_not(None))) or 0
    flagged = db.scalar(select(func.count(func.distinct(models.BatchSignal.batch))).where(models.BatchSignal.score >= 1.0)) or 0
    confirmed = db.scalar(select(func.count(models.Report.id)).where(models.Report.status == "confirmed")) or 0
    passports = db.scalar(select(func.count(func.distinct(models.SprayLog.plot_id)))) or 0
    views = db.scalar(select(func.count(models.PassportView.id))) or 0
    return {
        "scans": scans_n,
        "red_share": round(by_verdict.get("red", 0) / scans_n, 3) if scans_n else 0,
        "yellow_share": round(by_verdict.get("yellow", 0) / scans_n, 3) if scans_n else 0,
        "bills_checked": bills[0], "money_saved_rs": round(float(bills[1])),
        "money_saved_per_farmer_rs": round(float(bills[1]) / bills[2]) if bills[2] else 0,
        "sprays_logged": sprays_n, "sprays_with_safe_date": sprays_safe,
        "suspicious_batches_flagged": flagged, "reports_confirmed_by_officers": confirmed,
        "plots_with_passport": passports, "passport_views_by_buyers": views,
    }


@app.get("/fpo/plots")
def get_fpo_plots(db: Session = Depends(get_db)):
    """FPO / exporter view: every member plot with its spray record, flags and earliest safe harvest."""
    plots = db.scalars(select(models.SprayLog.plot_id).distinct()).all()
    return [spray.passport(db, p) for p in sorted(plots)]


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
def post_explain(req: schemas.ExplainRequest, db: Session = Depends(get_db)):
    """Retrieve the knowledge-base rows behind this verdict, then rephrase grounded only on them."""
    rows: list[dict] = []
    p = catalogue.product_by_id(db, req.product_id) if req.product_id else None
    if p is not None:
        card = catalogue.product_card(p)
        rows.append({"table": "products", "brand": card["brand"], "formulation": card["formulation"],
                     "moa_group": card["moa_group"], "toxicity_colour": card["toxicity_colour"]})
        crop_c = normalise.claim_crop(req.crop)
        for c in catalogue.claims_for(db, p.formulation):
            if crop_c is None or c["crop"] == crop_c:
                rows.append({"table": "label_claims", **{k: c[k] for k in ("crop", "pest", "dose_form_ha", "unit",
                                                                             "phi_days", "source_file", "page")}})
    for opt in catalogue.approved_for(db, req.crop, req.pest, limit=3) if req.crop else []:
        rows.append({"table": "approved_options", "formulation": opt["formulation"], "phi_days": opt["claim"]["phi_days"]})
    return {**explain_mod.explain(req.fired, _lang(req.lang), rows), "source_rows": rows}


@app.get("/uploads/{kind}/{name}", include_in_schema=False)
def get_upload(kind: str, name: str):
    """Stored photos, from the bucket or local disk (the bucket itself can stay private)."""
    data = storage.read_image(kind, name)
    if data is None:
        raise HTTPException(404, "not found")
    media = extract._media_type(data) or "application/octet-stream"
    return Response(data, media_type=media, headers={"Cache-Control": "private, max-age=86400"})

_DIST = Path(config.ROOT / "frontend" / "dist")
if _DIST.exists():
    app.mount("/app/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/app/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = _DIST / path
        return FileResponse(f if path and f.is_file() else _DIST / "index.html")
