# ML Service — optimized for Railway (CPU-only, memory-efficient)
# Root Directory in Railway must be set to: apps/ml-service
# Build context = apps/ml-service/
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (saves ~1.5GB vs default CUDA build)
RUN pip install --no-cache-dir \
    torch==2.1.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
# Context root = apps/ml-service/, so paths are relative to that
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformer model at build time
COPY download_models.py .
RUN python download_models.py

# Copy application code (everything in apps/ml-service/)
COPY . /app

# Create registry directory for model checkpoints
RUN mkdir -p /app/registry

ENV PYTHONPATH="/app"

EXPOSE 8080

# Use sh -c for $PORT expansion (Railway injects PORT dynamically)
CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 75"]
