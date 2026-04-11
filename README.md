# Podlink - Backend Suite

This folder contains the complete backend infrastructure for Podlink, including:
*   **Backend API** (FastAPI)
*   **ML Service** (PyTorch/Faiss)
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
*   `libs/shared`: Shared Python utilities used by all services.
