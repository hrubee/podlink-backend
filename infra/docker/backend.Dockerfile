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

# Run Alembic migrations then start the server.
# `alembic upgrade head` is idempotent — safe to run on every deploy.
CMD ["/bin/sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75"]

