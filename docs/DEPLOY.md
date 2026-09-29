# Deploying DawaCheck

The same backend code (every endpoint, rule and feature) runs in all three options. They differ only in what the hosting platform can run.

| Playbook stack item | A. Vercel only | B. Vercel frontend + Render backend | C. Docker Compose (any VM) |
|---|---|---|---|
| FastAPI backend, all endpoints, rules R1–R13 | ✅ Python function `api/index.py` | ✅ | ✅ |
| PostgreSQL + PostGIS | ✅ attach Neon/Postgres (`DATABASE_URL`); PostGIS enabled if the provider allows | ✅ Render Postgres + `CREATE EXTENSION postgis` | ✅ `postgis/postgis` image |
| Label/bill OCR | Vision model reads the photo (the playbook's "Cloud OCR API" fallback; needs `ANTHROPIC_API_KEY`) | ✅ Tesseract in the image (+ vision/LLM if key set) | ✅ Tesseract |
| Redis queue + OCR worker | Runs inside the request (Vercel has no background workers) | ✅ Render Key Value + worker | ✅ `redis` + `worker` |
| Photo storage (MinIO/S3) | Small crops inline; set `S3_*` for a bucket (e.g. Cloudflare R2) | set `S3_*` or disk | ✅ MinIO |
| Frontend (farmer app, dashboard, passport page) | ✅ static files under `/app/` | ✅ Vercel | ✅ served by the backend |

Choose **C** or **B** if you want every item exactly as in the playbook's stack table; **A** is the quickest.

---

## A. Everything on Vercel
1. Import the repo in Vercel. Keep the **Root Directory as the repository root**. `vercel.json` sets the build (frontend) and the Python function (backend), so framework auto-detection is not used. If Vercel offers a multi-service setup, ignore it: this `vercel.json` already defines both parts.
2. Storage → add a **Postgres** database (Neon) to the project. It sets `DATABASE_URL` / `POSTGRES_URL`; the app converts the URL for psycopg 3 and seeds itself on first start. Without a database the app falls back to SQLite in `/tmp`, which is wiped between instances (fine for a quick look, not for a demo).
3. Settings → Environment Variables: `ANTHROPIC_API_KEY` (photo reading and "Why?"), `ADMIN_TOKEN`, `USER_HASH_SALT`. Optional: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
4. Deploy. Open `https://<project>.vercel.app/app/`. API docs: `/docs`. Health: `/health`.

Limits to know: requests are capped at 4.5 MB (the app shrinks photos before upload), and the function timeout is set to 60 s in `vercel.json`.

## B. Frontend on Vercel, full backend on Render
1. Render → New → **Blueprint** → this repo. `render.yaml` creates the API (Docker image with Tesseract), the OCR worker, Redis and PostgreSQL. Set `ADMIN_TOKEN` and `ANTHROPIC_API_KEY` when asked. In the database shell run `CREATE EXTENSION postgis;` if the app's automatic attempt was not allowed.
2. Vercel → import the repo, then add the environment variable `VITE_API_URL=https://<your-render-api>.onrender.com` and redeploy. The farmer app and dashboard then call the Render backend directly (CORS is open).

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
The full test suite (105 tests) on SQLite and on PostgreSQL + PostGIS. The Vercel function was imported in a clean environment with only the root `requirements.txt` (151 MB installed, under Vercel's 250 MB limit), and served `/health`, `/scan`, `/docs` and admin routes through the rewritten paths. The Vercel static layout was built. **Not run:** an actual Vercel or Render deploy, and `docker compose up`, since this environment has no Docker daemon and cannot reach vercel.com or render.com. The first real deploy is the final check.
