from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.ranking import RankingService
from app.services.vector_search import VectorSearchService
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ML Recommendation Service")

# Model singletons
ranker = None
vector_store = VectorSearchService()

class RankRequest(BaseModel):
    user_id: int
    candidate_ids: List[int]
    top_k: Optional[int] = 10

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10

class IngestRequest(BaseModel):
    items: List[Dict[str, Any]] # List of {"id": "...", "text": "...", "metadata": {...}}

@app.on_event("startup")
async def startup():
    global ranker
    try:
        ranker = RankingService()
        logger.info("Ranking service loaded.")
    except Exception as e:
        logger.warning(f"Ranking model not found, running in lightweight mode: {e}")
    
    try:
        vector_store.load_index()
    except Exception as e:
        logger.warning(f"Vector index not found, starting fresh: {e}")

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "ranking_engine": ranker is not None,
        "vector_count": len(vector_store.metadata)
    }

@app.post("/search")
async def semantic_search(request: SearchRequest):
    """Find candidates similar to the query text."""
    results = vector_store.search(request.query, request.top_k)
    return {"results": results}

@app.post("/ingest-vectors")
async def ingest_vectors(request: IngestRequest, background_tasks: BackgroundTasks):
    """Add new items to the vector index."""
    ids = [item["id"] for item in request.items]
    texts = [item["text"] for item in request.items]
    
    # In a real system, this would be a background task
    vector_store.add_texts(ids, texts)
    vector_store.save_index()
    
    return {"status": "ingested", "count": len(ids)}

@app.post("/rank")
async def rank_candidates(request: Dict[str, Any]):
    """
    Ranks candidates using a hybrid approach:
    1. If NCF model scores are available, use them.
    2. Fallback/Augment with content-based similarity (topics, audience, language).
    """
    user_id = request.get("user_id")
    candidates = request.get("candidates", []) # List of dicts with id, topics, bio, etc.
    user_metadata = request.get("user_metadata", {})
    
    if not candidates:
        return {"ranked_ids": [], "scores": []}

    ranked_results = []
    
    for cand in candidates:
        score = 0.0
        
        # 0. Language Match (CRITICAL - 0.3)
        u_lang = user_metadata.get("language", "English")
        c_lang = cand.get("language", "English")
        if u_lang == c_lang:
            score += 0.3
        elif u_lang[:2].lower() == c_lang[:2].lower(): # Match "En" with "English"
            score += 0.2

        # 1. Topics Overlap (Weighted - 0.3)
        user_topics = set(user_metadata.get("topics", []))
        cand_topics = set(cand.get("topics", []))
        if user_topics:
            overlap = len(user_topics.intersection(cand_topics))
            score += (overlap / len(user_topics)) * 0.3
            
        # 2. Semantic Bio Similarity (0.3)
        if vector_store and user_metadata.get("bio") and cand.get("bio"):
            try:
                u_emb = vector_store.model.encode([user_metadata["bio"]])
                c_emb = vector_store.model.encode([cand["bio"]])
                import numpy as np
                sim = np.dot(u_emb[0], c_emb[0]) / (np.linalg.norm(u_emb[0]) * np.linalg.norm(c_emb[0]))
                score += float(sim) * 0.3
            except Exception as e:
                print(f"Embedding error: {e}")
            
        # 3. Target Audience Alignment (0.1)
        if user_metadata.get("target_audience") == cand.get("target_audience"):
            score += 0.1
            
        ranked_results.append({
            "id": cand["id"],
            "score": score
        })
        
    # Sort by score
    ranked_results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "ranked_ids": [r["id"] for r in ranked_results],
        "scores": [r["score"] for r in ranked_results]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
