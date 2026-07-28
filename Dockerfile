# Medical-PDF-annotator — FastAPI serving the pre-built frontend (backend/static).
# Docker (instead of native Python) so we can install the Tesseract OCR engine,
# which the auto-annotation/scanned-page OCR needs at runtime.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps: Tesseract OCR engine + English language data.
# On Linux the code (backend/app/text_extractor.py) uses `tesseract` from PATH
# and relies on Tesseract's default tessdata location, both provided by apt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements-server.txt ./
RUN pip install -r requirements-server.txt

# App code + pre-built frontend (backend/static). Copying backend/ into /app
# keeps config.py's paths valid: bundle dir = /app, static = /app/static.
COPY backend/ /app/

EXPOSE 10000
# $PORT is provided by Render; default 10000 for local runs.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
