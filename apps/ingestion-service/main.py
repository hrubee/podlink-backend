from fastapi import FastAPI, BackgroundTasks, HTTPException
from app.tasks.scheduler import setup_scheduler
from app.clients.podchaser import PodchaserClient
from app.db.storage import RedisCache, SessionLocal, PodcastEntity
from app.utils.normalizer import PodcastNormalizer
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Ingestion Service")
podchaser = PodchaserClient()
cache = RedisCache()

@app.on_event("startup")
async def startup_event():
    setup_scheduler()

@app.get("/health")
def health():
    return {"status": "ready"}

@app.get("/search/podcasts")
async def search_podcasts(q: str, limit: int = 10, page: int = 1):
    """Search Podchaser's podcast database by keyword."""
    try:
        results = await podchaser.search_podcasts(q, first=limit, page=page)
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/creators")
async def search_creators(q: str, limit: int = 10, page: int = 1):
    """Search Podchaser's creator database (hosts/guests) by name."""
    try:
        results = await podchaser.search_creators(q, first=limit, page=page)
        return results
    except Exception as e:
        logger.error(f"Creator search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/discover/trending")
async def get_trending(limit: int = 20):
    """Get trending/popular podcasts from Podchaser."""
    try:
        results = await podchaser.get_trending_podcasts(first=limit)
        return results
    except Exception as e:
        logger.error(f"Failed to get trending: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/creator/{creator_id}")
async def get_creator(creator_id: str):
    """Get detailed information about a creator including their podcast appearances."""
    try:
        results = await podchaser.get_creator_details(creator_id)
        return results
    except Exception as e:
        logger.error(f"Failed to get creator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/podcast/{podcast_id}")
async def get_podcast(podcast_id: str):
    """Get detailed information about a specific podcast."""
    try:
        results = await podchaser.get_podcast_details(podcast_id)
        return results
    except Exception as e:
        logger.error(f"Failed to get podcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/podcast/{podcast_id}")
async def trigger_ingestion(podcast_id: str, background_tasks: BackgroundTasks):
    """Trigger manual ingestion for a specific podcast."""
    # Check cache first
    cached_data = cache.get_podcast(podcast_id)
    if cached_data:
        return {"status": "cached", "data": cached_data}
    
    background_tasks.add_task(process_podcast_ingestion, podcast_id)
    return {"status": "ingestion_triggered", "podcast_id": podcast_id}

async def process_podcast_ingestion(podcast_id: str):
    try:
        raw_data = await podchaser.get_podcast_details(podcast_id)
        if not raw_data or not raw_data.get("podcast"):
            logger.error(f"No data found for podcast {podcast_id}")
            return

        # 1. Normalize
        normalized = PodcastNormalizer.normalize_podchaser_podcast(raw_data)
        
        # 2. Persist to DB
        with SessionLocal() as db:
            entity = db.query(PodcastEntity).filter(PodcastEntity.external_id == podcast_id).first()
            if not entity:
                entity = PodcastEntity(external_id=podcast_id)
                db.add(entity)
            
            entity.title = normalized.title
            entity.description = normalized.description
            entity.rating = normalized.rating
            entity.categories = normalized.categories
            entity.metadata_json = normalized.model_dump(mode='json')
            db.commit()

        # 3. Update Cache
        cache.set_podcast(podcast_id, normalized.model_dump(mode='json'))
        
        # 4. Push to ML Service for Vector Search
        import httpx
        from app.core.config import settings
        
        ml_url = f"{settings.ML_SERVICE_URL}/ingest-vectors"
        async with httpx.AsyncClient() as client:
            try:
                # Use description or title for vectorization
                text_to_vector = f"{normalized.title}. {normalized.description or ''}"
                await client.post(ml_url, json={
                    "items": [{"id": podcast_id, "text": text_to_vector}]
                })
                logger.info(f"Vector indexed for: {normalized.title}")
            except Exception as e:
                logger.warning(f"Failed to push vector to ML service: {e}")

        logger.info(f"Successfully ingested podcast: {normalized.title}")
        
    except Exception as e:
        logger.error(f"Ingestion failed for {podcast_id}: {str(e)}")

@app.post("/training/bulk-ingest")
async def trigger_bulk_ingestion(
    num_trending: int = 50,
    background_tasks: BackgroundTasks = None
):
    """
    Trigger bulk ingestion of Podchaser data for AI training.
    This will fetch trending podcasts and creators and ingest them into the ML service.
    """
    async def run_bulk_ingest():
        try:
            from app.training.bulk_ingest import BulkIngestionPipeline
            pipeline = BulkIngestionPipeline()
            results = await pipeline.run_bulk_ingestion(num_trending=num_trending)
            logger.info(f"Bulk ingestion completed: {results}")
        except Exception as e:
            logger.error(f"Bulk ingestion failed: {e}")
    
    if background_tasks:
        background_tasks.add_task(run_bulk_ingest)
        return {
            "status": "bulk_ingestion_triggered",
            "num_trending": num_trending,
            "message": "Training data ingestion started in background"
        }
    else:
        await run_bulk_ingest()
        return {"status": "completed"}

@app.get("/training/status")
async def get_training_status():
    """Get the current status of the ML service and training data."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://ml-service:8001/health")
            ml_status = response.json()
        
        return {
            "ml_service": ml_status,
            "ingestion_service": "ready",
            "podchaser_connected": True
        }
    except Exception as e:
        return {
            "ml_service": "unavailable",
            "ingestion_service": "ready",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
