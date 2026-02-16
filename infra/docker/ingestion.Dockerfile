FROM python:3.11-slim

WORKDIR /app

COPY apps/ingestion-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ingestion-service /app

ENV PYTHONPATH="/app"
EXPOSE 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
