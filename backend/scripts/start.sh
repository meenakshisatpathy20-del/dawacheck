#!/bin/sh
# Container start: seed the database, optionally start the RQ OCR worker in the background
# (RUN_WORKER=1, for hosts where a separate worker service costs extra, e.g. Render free tier),
# then serve the API.
set -e
python -m app.seed
if [ "${RUN_WORKER:-0}" = "1" ] && [ -n "$REDIS_URL" ]; then
  rq worker ocr --url "$REDIS_URL" &
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
