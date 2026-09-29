# Deploying DawaCheck

The same backend code (every endpoint, rule and feature) runs in all three options. They differ only in what the hosting platform can run.

| Playbook stack item | A. Vercel only | B. Vercel frontend + Render backend | C. Docker Compose (any VM) |
|---|---|---|---|
| FastAPI backend, all endpoints, rules R1–R13 | ✅ backend service (`backend/`, FastAPI) at `/api` | ✅ | ✅ |
| PostgreSQL + PostGIS | ✅ attach Neon/Postgres (`DATABASE_URL`); PostGIS enabled if the provider allows | ✅ Render Postgres + `CREATE EXTENSION postgis` | ✅ `postgis/postgis` image |
| Label/bill OCR | Vision model reads the photo (the playbook's "Cloud OCR API" fallback; needs `ANTHROPIC_API_KEY`) | ✅ Tesseract in the image (+ vision/LLM if key set) | ✅ Tesseract |
| Redis queue + OCR worker | Runs inside the request (Vercel has no background workers) | ✅ Render Key Value + worker | ✅ `redis` + `worker` |
| Photo storage (MinIO/S3) | Small crops inline; set `S3_*` for a bucket (e.g. Cloudflare R2) | set `S3_*` or disk | ✅ MinIO |
| Frontend (farmer app, dashboard, passport page) | ✅ frontend service (`frontend/`, Vite) at `/` | ✅ Vercel | ✅ served by the backend at `/app/` |

Choose **C** or **B** if you want every item exactly as in the playbook's stack table; **A** is the quickest.

---

## A. Everything on Vercel (multi-service project)
`vercel.json` defines two services, exactly as Vercel detects the repo: **backend** (`backend/`, FastAPI, served at `/api`) and **frontend** (`frontend/`, Vite, served at `/`).
1. Import the repository in Vercel and choose the **multi-service / Services** option (not "Import single project"). Vercel reads `vercel.json`; if the import page still says a `vercel.json` is needed, press its refresh button so it re-reads the branch.
2. Storage → add a **Postgres** database (Neon) to the project. It sets `DATABASE_URL` / `POSTGRES_URL`; the backend converts the URL for psycopg 3 and seeds itself on first start. Without a database the backend uses SQLite in `/tmp`, which is wiped between instances (fine for a quick look, not for a demo).
3. Environment Variables: `ANTHROPIC_API_KEY` (photo reading and "Why?"), `ADMIN_TOKEN`, `USER_HASH_SALT`. Optional: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
4. Deploy. Open `https://<project>.vercel.app/`. API: `/api/health`, docs at `/api/docs`. Screens use `/#/...` links (e.g. `/#/officer`) so any page can be reloaded.

How it fits together: the frontend build detects Vercel (`VERCEL=1`) and builds for `/` with the API at `/api`; the backend answers on both `/api/x` and `/x`, so it works whether Vercel forwards or strips the `/api` prefix. The backend service installs only `backend/requirements.txt` (slim, under the serverless size limit); on Vercel label and bill photos are read by the vision model, OCR jobs run inside the request, and small image crops are returned inline. Requests are capped at 4.5 MB (the app shrinks photos before upload).

## B. Frontend on Vercel, full backend on Render
1. Render → New → **Blueprint** → this repo. `render.yaml` creates the API (Docker image with Tesseract), the OCR worker, Redis and PostgreSQL. Set `ADMIN_TOKEN` and `ANTHROPIC_API_KEY` when asked. In the database shell run `CREATE EXTENSION postgis;` if the app's automatic attempt was not allowed.
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
The full test suite (106 tests) on SQLite and on PostgreSQL + PostGIS. A local stand-in for the Vercel services layout (frontend build at `/`, backend at `/api`, serverless mode, only the slim `backend/requirements.txt` installed) was driven in Chromium: scan → confirm → verdict, reloads, SOS, officer map, `/api/docs`, with every API call going to `/api/...` and no errors. **Not run:** an actual Vercel or Render deploy, and `docker compose up`, since this environment has no Docker daemon and cannot reach vercel.com or render.com. The first real deploy is the final check.
