# One image: builds the React app, then serves it and the API from FastAPI.
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# libgl/glib for OpenCV (QR decode); tesseract as a light OCR fallback. PaddleOCR is optional (see README).
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt pytesseract
COPY backend/ backend/
COPY data/ data/
COPY pipeline/ pipeline/
COPY --from=web /web/dist frontend/dist
WORKDIR /srv/backend
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD python -c "import os,urllib.request;urllib.request.urlopen('http://localhost:%s/health' % os.getenv('PORT','8000'))"
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
