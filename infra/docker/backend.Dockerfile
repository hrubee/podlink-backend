# Multi-stage build for FastAPI Backend
FROM python:3.11-slim as builder

WORKDIR /app
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY apps/backend /app


ENV PYTHONPATH="/app:/libs"
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
