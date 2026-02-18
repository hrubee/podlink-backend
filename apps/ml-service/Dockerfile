# ML Service — optimized for Railway (CPU-only, memory-efficient)
# Railway Root Directory: apps/ml-service
# Build context root = apps/ml-service/ — all COPY paths are relative to here
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers \
    # Force pip to use the CPU index for torch packages
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install ALL requirements in one pip call.
# By setting PIP_EXTRA_INDEX_URL above, torch==2.1.1+cpu and
# torchvision==0.16.1+cpu are resolved from the CPU wheel index.
# pip will NOT upgrade to the CUDA build because the versions are pinned.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformer model at build time
COPY download_models.py .
RUN python download_models.py

# Copy all application code
COPY . /app

# Ensure registry directory exists for model checkpoints
RUN mkdir -p /app/registry

ENV PYTHONPATH="/app"

EXPOSE 8001

# sh -c ensures $PORT is shell-expanded (Railway injects PORT at runtime)
CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001} --workers 1 --timeout-keep-alive 75"]
