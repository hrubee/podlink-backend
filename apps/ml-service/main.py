"""
ML Recommendation Service — FastAPI app

Endpoints:
  GET  /health          — Service status + model info
  POST /rank            — Hybrid rank candidates for a user
  POST /search          — Semantic search via FAISS
  POST /ingest-vectors  — Add profiles to vector index
  POST /train           — Trigger NCF model retraining
  GET  /model-info      — Current model metadata
"""
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.services.vector_search import VectorSearchService
from app.services.ranking import HybridRanker
from app.services.training import run_training

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# ── Singletons ────────────────────────────────────────────────────────────────
vector_store: Optional[VectorSearchService] = None
ranker: Optional[HybridRanker] = None
_training_lock = asyncio.Lock()
_is_training = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store, ranker
    logger.info("Starting ML service...")

    # Load vector store
    vector_store = VectorSearchService()
    try:
        vector_store.load_index()
        logger.info(f"Vector index loaded — {len(vector_store.metadata)} profiles indexed.")
    except Exception as e:
        logger.warning(f"No vector index found, starting fresh: {e}")

    # Load hybrid ranker (loads NCF if available)
    ranker = HybridRanker(vector_store=vector_store)
    logger.info("Hybrid ranker ready.")

    yield

    logger.info("ML service shutting down.")


app = FastAPI(title="PodMatch ML Service", version="2.0.0", lifespan=lifespan)


# ── Request / Response Models ─────────────────────────────────────────────────

class RankRequest(BaseModel):
    user_id: int
    user_metadata: Dict[str, Any]           # All profile fields
    candidates: List[Dict[str, Any]]        # List of candidate profiles
    total_interactions: int = 0             # Total likes in DB — controls NCF blend weight

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

class IngestRequest(BaseModel):
    items: List[Dict[str, Any]]             # [{"id": str, "text": str, "metadata": {...}}]

class TrainRequest(BaseModel):
    interactions: List[Dict[str, Any]]      # [{"actor_id": int, "target_id": int, "type": "like"}]
    epochs: int = 10
    batch_size: int = 256
    lr: float = 0.001

class IndexAddRequest(BaseModel):
    """Single-profile index update — called after user onboarding."""
    id: int
    bio: str = ""
    topics: List[str] = []
    target_audience: str = ""
    language: str = "English"
    engagement_style: List[str] = []
    interview_format: str = "both"
    episode_length_pref: str = "45-60"
    content_rating: str = "clean"
    fee_expectation: str = "free"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    ncf_loaded = ranker is not None and ranker._ncf_model is not None
    return {
        "status": "ok",
        "ncf_model_loaded": ncf_loaded,
        "ncf_version": ranker._model_meta.get("version") if (ranker and ranker._model_meta) else None,
        "vector_index_size": len(vector_store.metadata) if vector_store else 0,
        "is_training": _is_training,
    }


@app.get("/model-info")
def model_info():
    if ranker is None or ranker._model_meta is None:
        return {"status": "no_model", "message": "No trained NCF model yet. Using content-based ranking only."}
    return {
        "status": "loaded",
        **ranker._model_meta,
        "id_map_users": ranker._id_map["users"] if ranker._id_map else {},
        "id_map_items_count": len(ranker._id_map["items"]) if ranker._id_map else 0,
    }


@app.post("/rank")
async def rank_candidates(request: RankRequest):
    """
    Hybrid rank: content-based + NCF blended.
    NCF weight increases automatically as total_interactions grows.
    """
    if ranker is None:
        raise HTTPException(status_code=503, detail="Ranker not initialized.")

    if not request.candidates:
        return {"ranked_ids": [], "scores": [], "debug": []}

    results = ranker.rank(
        user_id=request.user_id,
        user_metadata=request.user_metadata,
        candidates=request.candidates,
        total_interactions=request.total_interactions,
    )

    return {
        "ranked_ids": [r["id"] for r in results],
        "scores": [r["score"] for r in results],
        "debug": results,  # Full breakdown for transparency
    }


@app.post("/search")
async def semantic_search(request: SearchRequest):
    """Semantic search over the FAISS vector index."""
    if vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized.")
    results = vector_store.search(request.query, request.top_k)
    return {"results": results}


@app.post("/ingest-vectors")
async def ingest_vectors(request: IngestRequest, background_tasks: BackgroundTasks):
    """Add/update profiles in the FAISS vector index."""
    if vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized.")

    ids = [str(item["id"]) for item in request.items]
    texts = [item.get("text", "") for item in request.items]

    if not texts:
        return {"status": "skipped", "count": 0}

    def _ingest():
        vector_store.add_texts(ids, texts)
        vector_store.save_index()
        logger.info(f"Ingested {len(ids)} profiles into vector index.")

    background_tasks.add_task(_ingest)
    return {"status": "ingesting", "count": len(ids)}


@app.post("/train")
async def trigger_training(request: TrainRequest, background_tasks: BackgroundTasks):
    """
    Trigger NCF model retraining in the background.
    Only one training job can run at a time.
    Requires at least 10 positive interactions (likes).
    """
    global _is_training

    if _is_training:
        raise HTTPException(status_code=409, detail="Training already in progress.")

    likes = [i for i in request.interactions if i.get("type") == "like"]
    if len(likes) < 10:
        return {
            "status": "skipped",
            "reason": f"Need at least 10 likes to train NCF. Currently have {len(likes)}.",
            "likes_count": len(likes),
        }

    async def _train_job():
        global _is_training, ranker
        _is_training = True
        try:
            logger.info(f"Starting NCF training with {len(likes)} interactions...")
            result = run_training(
                interactions=request.interactions,
                epochs=request.epochs,
                batch_size=request.batch_size,
                lr=request.lr,
            )
            logger.info(f"Training complete: {result}")
            # Reload the ranker with the new model
            ranker = HybridRanker(vector_store=vector_store)
            logger.info("Ranker reloaded with new NCF model.")
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
        finally:
            _is_training = False

    background_tasks.add_task(_train_job)

    return {
        "status": "started",
        "message": f"Training started with {len(likes)} interactions.",
        "epochs": request.epochs,
    }


@app.post("/index/add")
async def add_to_index(request: IndexAddRequest):
    """
    Add or update a single user profile in the FAISS vector index.
    Called automatically after a user completes onboarding so they
    appear in semantic search and recommendations immediately.
    """
    if vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized.")

    # Build a rich text representation for embedding
    topics_str = ", ".join(request.topics) if request.topics else ""
    style_str = ", ".join(request.engagement_style) if request.engagement_style else ""
    text = (
        f"{request.bio} "
        f"Topics: {topics_str}. "
        f"Audience: {request.target_audience}. "
        f"Language: {request.language}. "
        f"Style: {style_str}. "
        f"Format: {request.interview_format}. "
        f"Length: {request.episode_length_pref}. "
        f"Rating: {request.content_rating}. "
        f"Fee: {request.fee_expectation}."
    ).strip()

    metadata = request.model_dump()
    metadata.pop("bio", None)  # bio is already in text

    vector_store.add_or_update(str(request.id), text, metadata)
    vector_store.persist_index()

    return {
        "status": "indexed",
        "user_id": request.id,
        "index_size": len(vector_store.metadata),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
