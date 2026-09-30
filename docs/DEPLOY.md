# Deploying DawaCheck

The same backend code (every endpoint, rule and feature) runs in all three options. They differ only in what the hosting platform can run.

| Playbook stack item | A. Vercel only | B. Vercel frontend + Render backend | C. Docker Compose (any VM) |
|---|---|---|---|
| FastAPI backend, all endpoints, rules R1–R13 | ✅ backend service (`backend/`, FastAPI) at `/api` | ✅ | ✅ |
| PostgreSQL + PostGIS | ✅ attach Neon/Postgres (`DATABASE_URL`); PostGIS enabled if the provider allows | ✅ Render Postgres + `CREATE EXTENSION postgis` | ✅ `postgis/postgis` image |
| Label/bill OCR | Vision model reads the photo (the playbook's "Cloud OCR API" fallback; needs `ANTHROPIC_API_KEY`) | ✅ Tesseract in the image (+ vision/LLM if key set) | ✅ Tesseract |
| Redis queue + OCR worker | Upstash QStash queue: each job runs in its own function call (inside the request if QStash is not set) | ✅ Render Key Value + RQ worker in the API container (`RUN_WORKER=1`, free tier) | ✅ `redis` + `worker` |
| Photo storage (MinIO/S3) | Small crops inline; set `S3_*` for a bucket (e.g. Cloudflare R2) | set `S3_*` or disk | ✅ MinIO |
| Frontend (farmer app, dashboard, passport page) | ✅ frontend service (`frontend/`, Vite) at `/` | ✅ Vercel | ✅ served by the backend at `/app/` |

Choose **C** or **B** if you want every item exactly as in the playbook's stack table; **A** is the quickest.

---

## A. Everything on Vercel (one project)
`vercel.json` builds the React app (`frontend/`) into static files at `/`, and runs the complete FastAPI backend (`backend/app`, every endpoint) as one Python function, `api/index.py`, at `/api/...`.
1. Vercel → **Add New → Project** → import `dawacheck`. On the import page choose **Import single project** for the repository root (Root Directory `./`), **not** the `backend` / `frontend` entries and **not** Services. Framework Preset: **Other** (the build settings come from `vercel.json`).
2. Environment Variables: `ADMIN_TOKEN`, `USER_HASH_SALT`, and optionally `ANTHROPIC_API_KEY`. Deploy.
   For the background queue add, from console.upstash.com → QStash: `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY` (or install the Upstash QStash integration from the Vercel Marketplace, which sets them).
3. Storage → **Create Database → Neon (Postgres)** → connect to the project, then **Redeploy**. The backend creates its tables and loads the demo data on first start.
4. Open `https://<project>.vercel.app/` (website), `/#/officer` (dashboard), `/api/health`, `/api/docs`. `/api/health` must show `"db": "postgresql+psycopg"` and an empty `warnings` list; any warning says what is still missing.

On Vercel:
- **Photo reading:** with `ANTHROPIC_API_KEY`, the vision model reads label and bill photos on the server; without it, the phone reads them itself (Tesseract compiled to WebAssembly, files served from `/ocr/`, cached for offline).
- **Queue:** Vercel has no background workers, so with the QStash variables set the app stores each OCR job in the `jobs` table and asks Upstash QStash to call the signed `POST /api/jobs/run`; the job then runs in its own function call while the phone polls `/api/jobs/{id}`. This needs the shared Postgres from step 3 (the public URL comes from Vercel; set `PUBLIC_URL` for a custom domain). Without QStash, jobs run inside the request.
- **Photos:** kept in any S3-compatible bucket when `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` (and `S3_REGION`, `auto` for Cloudflare R2) are set; the backend serves them at `/api/uploads/...`, so the bucket stays private. Without a bucket, only the small field crops are kept (inline).
- Requests are capped at 4.5 MB; the app shrinks photos before upload.

## B. Frontend on Vercel, full backend on Render
1. Render → New → **Blueprint** → this repo. `render.yaml` creates the API (Docker image with Tesseract; the RQ OCR worker runs in the same container because `RUN_WORKER=1`), Redis and PostgreSQL, all on free plans. Set `ADMIN_TOKEN` and `ANTHROPIC_API_KEY` when asked. In the database shell run `CREATE EXTENSION postgis;` if the app's automatic attempt was not allowed.
2. Vercel → import only the **frontend** folder ("Import single project" on `frontend`), add the environment variable `VITE_API_URL=https://<your-render-api>.onrender.com` and deploy. The farmer app and dashboard then call the Render backend directly (CORS is open).

## C. Docker Compose on any VM
```bash
git clone -b claude/nice-hawking-3f7lua https://github.com/meenakshisatpathy20-del/dawacheck.git
cd dawacheck && cp .env.example .env   # set USER_HASH_SALT, ADMIN_TOKEN, ANTHROPIC_API_KEY
docker compose up -d --build           # app on :8000/app/
```
Put HTTPS in front (Caddy or Nginx): phones only open the camera on HTTPS pages. Change the demo database and MinIO passwords in `docker-compose.yml`.

---

## Before real farmers use it
Load the real CIB&RC data (`python -m pipeline.run --download --load`), check demo products against the PDF pages, replace the fictional catalogue, and have the translations reviewed. Until then the app shows a "sample data" notice.

## Verified in the build environment
The full test suite on SQLite and on PostgreSQL + PostGIS. A local stand-in for the Vercel project (frontend build at `/`, `api/index.py` behind the `/api/:path*` rewrite, serverless mode, only the root `requirements.txt` installed) was driven in Chromium in both ways Vercel can hand the request to the function: scanning a label photo read on the phone, verdict, officer map, `/api/docs`, with no errors. The QStash path is covered by tests (signature check, stored job, polling, fallback). **Not run:** an actual Vercel or Render deploy, a live QStash delivery, and `docker compose up` (no access from the build environment).
