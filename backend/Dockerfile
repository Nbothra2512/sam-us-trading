# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
RUN mkdir -p /app/data
ENV DATA_DIR=/app/data
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
