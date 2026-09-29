# DawaCheck

**Plantix tells you the disease. DawaCheck tells you whether the pesticide the dealer handed you is genuine, approved for your crop, safe to mix, and when your harvest is safe to sell.**

DawaCheck is a voice-first app that checks a pesticide at the moment of purchase: is it registered, approved for this crop and pest, safe to mix, and how much to spray. It then follows the spray through to a safe harvest date. Built for the AgriTech track from the *DawaCheck: Complete Hackathon Playbook*.

> **AI reads, rules decide.** OCR and an LLM only turn photos and text into structured fields. Every verdict, dose and date comes from a deterministic rules engine (R1–R13, stored as data) that cites its source file and page.

## ⚠️ Read this before any demo or field use

| What | Status |
|---|---|
| Label claims (crop × pest × dose × waiting period) in `data/seed/label_claims.json` | **SAMPLE DATA.** Not yet parsed from the CIB&RC *Major Uses* PDFs; marked `verified: false` and shown in the app as sample data. Run `pipeline/` on the official PDFs to replace them (see [Data pipeline](#data-pipeline)). |
| Product catalogue (`data/seed/products.json`) | **Fictional brands, companies and registration numbers**, so no real company is misrepresented. Replace with products built from the CIB&RC registered-products list and labels you photograph. |
| Banned / restricted flags, IRAC/FRAC groups, toxicity colours | Hand-made enrichment table. Re-check bans against the current CIB&RC list; copy toxicity colours from each real label. |
| Facts on slides (Yavatmal, 52% credit, 20% read labels, 2.8% above MRL, EU detections, Punjab basmati ban) | Taken from the sources linked in the playbook; see [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). Re-open each source before quoting it. |
| Hindi, Marathi, Punjabi text | Drafts. Review with native speakers. |

A verdict never says "fake". It says "not found in the government registry" or "reported by other farmers". Only a lab test proves a product is spurious.

## Quick start

### One command (Docker)
```bash
cp .env.example .env          # optional: add ANTHROPIC_API_KEY for LLM extraction
docker compose up --build
```
Open **http://localhost:8000/app/** (farmer app), **/app/officer** (dashboard), **/docs** (API). The stack is PostgreSQL + PostGIS, Redis, MinIO and the app.

### Without Docker (laptop demo, SQLite)
```bash
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
cd backend && python -m app.seed --reset && uvicorn app.main:app --port 8000
```
Frontend hot reload: `cd frontend && npm run dev` (proxies the API to :8000), then open http://localhost:5173/app/.

On stage with unreliable Wi-Fi set `DAWACHECK_OFFLINE=1`: no external calls; the spray-window check can be simulated with `/weather-window?demo=rain`.

### Tests
```bash
cd backend && python -m pytest -q          # 79 tests: rules, API, dose, extraction, pipeline, 30 KB questions
TEST_DATABASE_URL=postgresql+psycopg://user@host/db python -m pytest -q   # same suite on PostgreSQL
```

## What is built (playbook sections 5 and 6)

| # | Feature | Where |
|---|---|---|
| C1 | Scan: QR (on-device `BarcodeDetector`, server OpenCV), label photo OCR (PaddleOCR / Tesseract), LLM → strict JSON with regex fallback, fuzzy match (rapidfuzz), farmer confirms | `backend/app/ai/`, `services/scan.py`, `frontend/src/farmer/ScanPacket.jsx` |
| C2 | Registry check: registered formulation, reg. no. match, banned/restricted, expiry | rules R1–R4, G1 |
| C3 | Label-claim check for crop × pest, approved alternatives | rules R5, R6; `catalogue.approved_for` |
| C4 | Dose to tank: ml/g per tank and number of tanks; granules → kg per acre | `services/dose.py` |
| C5 | Waiting period → safe harvest date + reminder | `services/spray.py`, rule R12 |
| C6 | Toxicity colour, protective gear, label antidote, red-label confirmation | `scan.safety_card`, Result screen |
| C7 | Spray window from Open-Meteo (rain, wind, heat) | `services/weather.py`, rule R13 |
| C8 | Every verdict in English, Hindi, Marathi, Punjabi; spoken with the phone's TTS; colour + icon + sound | `backend/app/i18n/`, `frontend/src/voice.js` |
| W1 | Bill Scan: every line checked, same chemical for less ("seen near you") | `services/bill.py`, `Bill.jsx` |
| W2 | Cocktail Checker: duplicate a.i., same IRAC/FRAC group, toxicity stacking, jar-test hint | `services/mix.py`, rules R9–R11, M4 |
| W3 | MRL Passport: spray diary, latest safe date, state-ban and EU export flags, public QR page | `services/spray.py`, `Sprays.jsx`, `passport/Passport.jsx` |
| W4 | Doctor Card + Poison SOS: NPIC 1800 116 117, 108, first aid and antidote from the label, nearest health centres (OpenStreetMap) | `services/sos.py`, `Sos.jsx` |
| W5 | Resistance Rotation Planner on sample data | `spray.rotation`, rule R10 |
| W6 | Fake-Batch Radar on sample data: date conflicts, cloned QR, not in registry, farmer reports; map, ranked batches, batch timeline, FPO export view | `services/radar.py`, `frontend/src/officer/` |

API (section 11): `POST /scan`, `POST /bill`, `POST /mix-check`, `GET /claims`, `POST /dose`, `POST /spray-log`, `GET /passport/{plot_id}`, `GET /sos`, `GET /weather-window`, `POST /report`, `GET /radar`, `GET /health`, plus `/radar/batch`, `/rotation`, `/fpo/plots`, `/products`, `/crops`, `/offline-pack`, `/i18n/{lang}`, `/explain`. Interactive docs at `/docs`.

## Architecture

```
Farmer app (PWA)      Officer / FPO dashboard      MRL Passport page
        \                     |                          /
                    FastAPI backend (backend/app/main.py)
        |                     |                          |
 AI reading layer  ->   Rules engine R1-R13   <-   Supporting services
 QR, OCR, LLM->JSON     rules.json (data)          weather, SOS, radar
 fuzzy match            worst colour wins
                        cites file + page
        |                     |
 Photo storage         Knowledge base: PostgreSQL + PostGIS (SQLite for tests)
 MinIO / S3 / disk     label_claims, products, bans, export_flags, scans,
                       spray_log, batch_signals, prices, reports
                              ^
            Offline pipeline: CIB&RC PDFs -> pdfplumber/camelot -> normalise -> validate -> load
```

**Guardrails:** the LLM never outputs a verdict, dose or date; extraction must pass a JSON schema and regex cross-checks; low-confidence matches ask the farmer to confirm; the "Why?" rephrasing is discarded if it contains any number not in the fired rules; every scan is logged (image hash, extracted JSON, fired rules); phone numbers are never collected (a salted hash of a device id is stored); location only if the phone shares it.

## Data pipeline

```bash
# 1. put the real PDF links from ppqs.gov.in into pipeline/sources.json
python -m pipeline.run --download --load
# 2. review data/interim/review.csv, fix rows, then rewrite data/kb_questions.json answers from the PDF pages
cd backend && python -m pytest tests/test_kb_questions.py
```
The parser carries the chemical heading and crop down to each row, splits "Aphids, Jassids & Thrips" into separate claims, parses "1500-2500" into min/max and "--" into null, and keeps `source_file` + `page` on every row. It is tested on a synthetic PDF in the CIB&RC layout (`backend/tests/test_pipeline.py`). The real PDFs could not be fetched while building (the build environment's network policy blocked ppqs.gov.in), so run it where that site is reachable.

## Repository layout
```
backend/app/        FastAPI app: rules/, services/, ai/, i18n/, models, seed
backend/tests/      pytest suite
data/seed/          knowledge-base seed (sample label claims, fictional catalogue, bans, export flags)
data/kb_questions.json   30-question knowledge-base test set
pipeline/           CIB&RC PDF -> label_claims.json
frontend/           React + Vite: farmer PWA, officer dashboard, passport page
docs/               demo script, judge Q&A, data sources, checklist, pitch deck (.pptx + generator)
```

## Honest limits
- Tank-mix checks cover duplicates, resistance group and toxicity only; no prediction of chemical reactions.
- The MRL Passport is a self-declared record plus a risk estimate, not a lab certificate.
- The SOS screen repeats label text and routes to professionals; it gives no treatment advice of its own.
- The farmer app is a Progressive Web App (installable, camera, voice, offline cache) rather than Flutter/React Native: the playbook allows either, and a PWA let the whole stack be built and tested in one repository. Wrapping it with Capacitor or porting screens to Flutter is straightforward because all logic is in the API.

See [`docs/`](docs/) for the demo script, judge Q&A, sources and the final checklist.
