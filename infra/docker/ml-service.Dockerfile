# ML Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ML
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY apps/ml-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models during build to avoid runtime downloads
COPY apps/ml-service/download_models.py .
RUN python download_models.py

COPY apps/ml-service /app
COPY libs/shared/python /libs/shared

ENV PYTHONPATH="/app:/libs"
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
