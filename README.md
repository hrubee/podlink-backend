# PodMatch.AI - Backend Suite

This folder contains the complete backend infrastructure for PodMatch.AI, including:
*   **Backend API** (FastAPI)
*   **ML Service** (PyTorch/Faiss)
*   **Ingestion Service** (Podchaser Pipeline)
*   **Shared Libraries** & Infrastructure

## 🚀 Deployment (Railway / Render / VPS)

### Option A: Railway (Recommended)
1.  **Push to GitHub**: Push this entire folder to a new repository.
2.  **Import to Railway**: It will detect the `docker-compose.yml`.
3.  **Config**: Ensure you add your environment variables from `.env` to the Railway dashboard.

### Option B: Docker Compose (Self-Hosted)
```bash
docker-compose up -d --build
```

## 🛠 Project Structure
*   `apps/backend`: Primary API (Port 8000)
*   `apps/ml-service`: AI Ranking & Vector Search (Port 8001)
*   `apps/ingestion-service`: Data Pipeline (Port 8002)
*   `libs/shared`: Shared Python utilities used by all services.
