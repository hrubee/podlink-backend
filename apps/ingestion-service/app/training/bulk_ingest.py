"""
Bulk ingestion and training pipeline for Podchaser data.
This script fetches data from Podchaser and prepares it for ML training.
"""
import asyncio
import logging
from typing import List, Dict, Any
import httpx
import json
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.podchaser import PodchaserClient
from db.storage import SessionLocal, PodcastEntity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BulkIngestionPipeline:
    def __init__(self):
        self.podchaser = PodchaserClient()
        self.ml_service_url = "http://ml-service:8001"
        self.ingested_count = 0
        self.failed_count = 0
        
    async def fetch_trending_podcasts(self, limit: int = 100) -> List[Dict]:
        """Fetch trending podcasts for training data."""
        logger.info(f"Fetching {limit} trending podcasts...")
        try:
            result = await self.podchaser.get_trending_podcasts(first=limit)
            podcasts = result.get("podcasts", {}).get("data", [])
            logger.info(f"Fetched {len(podcasts)} trending podcasts")
            return podcasts
        except Exception as e:
            logger.error(f"Failed to fetch trending: {e}")
            return []
    
    async def search_podcasts_by_categories(self, categories: List[str], per_category: int = 20) -> List[Dict]:
        """Search podcasts across multiple categories."""
        all_podcasts = []
        for category in categories:
            try:
                logger.info(f"Searching podcasts in category: {category}")
                result = await self.podchaser.search_podcasts(category, first=per_category)
                podcasts = result.get("podcasts", {}).get("data", [])
                all_podcasts.extend(podcasts)
                logger.info(f"Found {len(podcasts)} podcasts for {category}")
                await asyncio.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to search {category}: {e}")
        
        # Deduplicate by ID
        unique_podcasts = {p["id"]: p for p in all_podcasts}.values()
        logger.info(f"Total unique podcasts: {len(unique_podcasts)}")
        return list(unique_podcasts)
    
    async def fetch_creators_for_training(self, search_terms: List[str], per_term: int = 20) -> List[Dict]:
        """Fetch creators across multiple search terms."""
        all_creators = []
        for term in search_terms:
            try:
                logger.info(f"Searching creators: {term}")
                result = await self.podchaser.search_creators(term, first=per_term)
                creators = result.get("creators", {}).get("data", [])
                all_creators.extend(creators)
                logger.info(f"Found {len(creators)} creators for {term}")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to search creators {term}: {e}")
        
        unique_creators = {c["pcid"]: c for c in all_creators}.values()
        logger.info(f"Total unique creators: {len(unique_creators)}")
        return list(unique_creators)
    
    async def ingest_podcast_to_ml(self, podcast: Dict) -> bool:
        """Send podcast data to ML service for vectorization."""
        try:
            text = f"{podcast.get('title', '')}. {podcast.get('description', '')}"
            categories = [c.get("title", "") for c in podcast.get("categories", [])]
            text += f" Categories: {', '.join(categories)}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ml_service_url}/ingest-vectors",
                    json={
                        "items": [{
                            "id": podcast["id"],
                            "text": text,
                            "metadata": {
                                "type": "podcast",
                                "title": podcast.get("title"),
                                "rating": podcast.get("ratingAverage"),
                                "categories": categories
                            }
                        }]
                    }
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to ingest podcast {podcast.get('id')}: {e}")
            return False
    
    async def ingest_creator_to_ml(self, creator: Dict) -> bool:
        """Send creator data to ML service for vectorization."""
        try:
            text = f"{creator.get('name', '')}. {creator.get('bio', '')} {creator.get('subtitleShort', '')}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ml_service_url}/ingest-vectors",
                    json={
                        "items": [{
                            "id": f"creator_{creator['pcid']}",
                            "text": text,
                            "metadata": {
                                "type": "creator",
                                "name": creator.get("name"),
                                "pcid": creator.get("pcid"),
                                "episode_count": creator.get("episodeAppearanceCount", 0)
                            }
                        }]
                    }
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to ingest creator {creator.get('pcid')}: {e}")
            return False
    
    async def run_bulk_ingestion(self, 
                                  num_trending: int = 100,
                                  categories: List[str] = None,
                                  creator_terms: List[str] = None):
        """Run the complete bulk ingestion pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING BULK INGESTION PIPELINE")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Default categories if not provided
        if categories is None:
            categories = [
                "technology", "business", "comedy", "education", 
                "health", "science", "sports", "news", "true crime",
                "entrepreneurship", "marketing", "AI", "startup"
            ]
        
        # Default creator search terms
        if creator_terms is None:
            creator_terms = [
                "entrepreneur", "CEO", "founder", "investor", "author",
                "scientist", "researcher", "host", "comedian", "expert"
            ]
        
        # Phase 1: Fetch trending podcasts
        logger.info("\n📊 PHASE 1: Fetching trending podcasts...")
        trending = await self.fetch_trending_podcasts(num_trending)
        
        # Phase 2: Search podcasts by category
        logger.info("\n🔍 PHASE 2: Searching podcasts by category...")
        category_podcasts = await self.search_podcasts_by_categories(categories, per_category=15)
        
        # Combine and deduplicate
        all_podcasts = list({p["id"]: p for p in (trending + category_podcasts)}.values())
        logger.info(f"\n✅ Total podcasts to ingest: {len(all_podcasts)}")
        
        # Phase 3: Ingest podcasts to ML service
        logger.info("\n🤖 PHASE 3: Ingesting podcasts to ML service...")
        for i, podcast in enumerate(all_podcasts, 1):
            if await self.ingest_podcast_to_ml(podcast):
                self.ingested_count += 1
            else:
                self.failed_count += 1
            
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(all_podcasts)} podcasts processed")
            await asyncio.sleep(0.5)  # Rate limiting
        
        # Phase 4: Fetch and ingest creators
        logger.info("\n👥 PHASE 4: Fetching and ingesting creators...")
        creators = await self.fetch_creators_for_training(creator_terms, per_term=10)
        
        for i, creator in enumerate(creators, 1):
            if await self.ingest_creator_to_ml(creator):
                self.ingested_count += 1
            else:
                self.failed_count += 1
            
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(creators)} creators processed")
            await asyncio.sleep(0.5)
        
        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "=" * 60)
        logger.info("BULK INGESTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"✅ Successfully ingested: {self.ingested_count}")
        logger.info(f"❌ Failed: {self.failed_count}")
        logger.info(f"⏱️  Duration: {duration:.2f} seconds")
        logger.info(f"📊 Rate: {self.ingested_count / duration:.2f} items/second")
        logger.info("=" * 60)
        
        return {
            "success": self.ingested_count,
            "failed": self.failed_count,
            "duration": duration,
            "podcasts": len(all_podcasts),
            "creators": len(creators)
        }

async def main():
    """Main entry point for bulk ingestion."""
    pipeline = BulkIngestionPipeline()
    
    # Run with custom parameters
    results = await pipeline.run_bulk_ingestion(
        num_trending=50,  # Fetch top 50 trending
        categories=[
            "technology", "business", "entrepreneurship", 
            "startup", "AI", "marketing", "sales",
            "leadership", "productivity", "investing"
        ],
        creator_terms=[
            "entrepreneur", "CEO", "founder", "investor",
            "tech", "startup", "business", "host"
        ]
    )
    
    logger.info(f"\n📈 Final Results: {json.dumps(results, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
