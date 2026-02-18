# Multi-stage build for FastAPI Backend
FROM python:3.11-slim AS builder

WORKDIR /app
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Python optimizations for containers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:/libs"

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY apps/backend /app

EXPOSE 8000

# Railway injects $PORT dynamically — default to 8000 for local Docker
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75

