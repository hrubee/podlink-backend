from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.clients.podchaser import PodchaserClient
from app.db.storage import RedisCache, SessionLocal, PodcastEntity
from app.utils.normalizer import PodcastNormalizer
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
client = PodchaserClient()
cache = RedisCache()

async def sync_podcasts_job():
    """Daily sync of priority podcasts."""
    logger.info("Starting scheduled Podchaser sync...")
    
    with SessionLocal() as db:
        # Fetch podcasts that haven't been updated in 24 hours
        stale_podcasts = db.query(PodcastEntity).all() # Simplified for demo
        
        for pod in stale_podcasts:
            try:
                raw_data = await client.get_podcast_details(pod.external_id)
                if not raw_data:
                    continue
                
                normalized = PodcastNormalizer.normalize_podchaser_podcast(raw_data)
                
                # Update DB
                pod.title = normalized.title
                pod.description = normalized.description
                pod.rating = normalized.rating
                pod.categories = normalized.categories
                pod.metadata_json = normalized.dict()
                pod.last_updated = datetime.utcnow()
                
                # Update Cache
                cache.set_podcast(pod.external_id, normalized.dict())
                
                # Sleep briefly to respect rate limits during batch processing
                import asyncio
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to sync {pod.external_id}: {e}")
        
    db.commit()
    logger.info("Daily sync completed.")

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    # Runs at 2 AM every night
    scheduler.add_job(sync_podcasts_job, 'cron', hour=2)
    scheduler.start()
    return scheduler
