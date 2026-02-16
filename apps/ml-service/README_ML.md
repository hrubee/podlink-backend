# Deployment & Data Pipeline Guide for Podcast AI ML

## 1. Recommendation Strategy
We use a **Hybrid Discovery Engine**:
- **Neural Collaborative Filtering (NCF):** Learns from the "Like" and "Match" interactions tracked by the Backend service. Uses Matrix Factorization + Deep Learning.
- **Content-Based Fallback:** Uses Sentence-Transformers (from `apps/ingestion-service`) to create profile embeddings. This handles users with 0 interactions (**Cold Start**).
- **External Boost:** Integrates Podchaser global rankings to suggest high-authority shows to new guests.

## 2. Model Pipeline
1. **Data Collection:** Every 24h, the `ml-service` pulls the `interactions` and `matches` tables from PostgreSQL.
2. **Preprocessing:** Maps IDs to continuous indices for integer embeddings.
3. **Training:** PyTorch NCF model trains for 10-20 epochs on current day's interaction snapshot.
4. **Validation:** Checks Hit Ratio @ 10 (HR@10) and Normalized Discounted Cumulative Gain (NDCG).
5. **Registry:** Saves model to `registry/model_YYYYMMDD.pt` and symlinks `latest.pt`.

## 3. Deployment
- **API:** FastAPI serves the model via `/rank`. It expects a list of `candidate_ids` (provided by the Backend after initial geo/niche filtering).
- **Inference:** $O(1)$ lookup for embeddings + forward pass.
- **GPU Support:** Automatically detects CUDA if available in the Docker environment.

## 4. Cold Start Resolution
When a user is brand new:
1. `RankingService.cold_start_resolver()` retrieves their profile embedding.
2. Performs a vector search against all podcasts.
3. Blends results with "Global Trending" podcasts from Podchaser.
