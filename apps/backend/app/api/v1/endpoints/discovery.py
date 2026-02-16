from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
try:
    import httpx
except ImportError:
    httpx = None
import logging
from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

INGESTION_SERVICE_URL = "http://ingestion-service:8002"

@router.get("/search/profiles")
async def search_profiles(
    q: str,
    type: Optional[str] = None,  # "host", "guest", or None for both
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for podcast hosts and guests.
    Prioritizes local database (seeded users) and falls back to Podchaser.
    """
    profiles = []
    
    # 1. Search Local Database First (Optimized for filters)
    try:
        query = db.query(User).filter(User.is_public == True)
        
        # Apply search filters
        search_filter = or_(
            User.full_name.ilike(f"%{q}%"),
            User.bio.ilike(f"%{q}%"),
            User.topics.cast(str).ilike(f"%{q}%") # Search within JSON topics
        )
        query = query.filter(search_filter)
        
        if type:
            query = query.filter(User.role == type.upper())
            
        local_users = query.limit(limit).all()
        
        for u in local_users:
            display_name = u.full_name or "User"
            safe_name = display_name.replace(" ", "+")
            profiles.append({
                "id": str(u.id),
                "name": display_name,
                "bio": u.bio,
                "image_url": f"https://ui-avatars.com/api/?name={safe_name}&background=6366f1&color=fff",
                "subtitle": f"{'Host' if u.role == 'HOST' else 'Guest'} • {u.location}",
                "topics": u.topics,
                "type": "internal"
            })
    except Exception as e:
        logger.warning(f"Local search failed: {e}")

    # 2. Fetch from External Service (Podchaser) if we need more results
    if len(profiles) < limit and httpx:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{INGESTION_SERVICE_URL}/search/creators",
                    params={"q": q, "limit": limit - len(profiles)}
                )
                if response.status_code == 200:
                    data = response.json()
                    creators = data.get("creators", {}).get("data", [])
                    for creator in creators:
                        profiles.append({
                            "id": creator.get("pcid"),
                            "name": creator.get("name"),
                            "bio": creator.get("bio", ""),
                            "image_url": creator.get("imageUrl"),
                            "subtitle": creator.get("subtitleShort", "Podcast Creator"),
                            "type": "external"
                        })
        except Exception as e:
            logger.error(f"External search failed: {e}")

    return {
        "profiles": profiles,
        "total": len(profiles)
    }

@router.get("/trending")
async def discover_trending(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discover trending podcasts and their hosts.
    Falls back to high-quality internal profiles if service is down.
    """
    items = []
    
    # 1. Try External Discovery
    if httpx:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{INGESTION_SERVICE_URL}/discover/trending",
                    params={"limit": limit}
                )
                if response.status_code == 200:
                    data = response.json()
                    podcasts = data.get("podcasts", {}).get("data", [])
                    for podcast in podcasts:
                        items.append({
                            "id": podcast.get("id"),
                            "title": podcast.get("title"),
                            "description": podcast.get("description", ""),
                            "image_url": podcast.get("imageUrl"),
                            "rating": podcast.get("ratingAverage"),
                            "categories": [c.get("title") for c in podcast.get("categories", [])],
                            "type": "podcast"
                        })
                    return {"items": items}
        except Exception as e:
            logger.warning(f"External trending failed: {e}")

    # 2. Hybrid Fallback: Return featured internal accounts
    try:
        featured = db.query(User).filter(User.onboarded == True).limit(limit).all()
        for u in featured:
            items.append({
                "id": str(u.id),
                "title": u.full_name,
                "description": u.bio,
                "image_url": f"https://ui-avatars.com/api/?name={u.full_name.replace(' ', '+')}&size=200&background=6366f1&color=fff",
                "categories": u.topics[:3] if u.topics else ["Podcast"],
                "type": "featured_profile"
            })
    except Exception as e:
        logger.error(f"Fallback trending failed: {e}")

    return {"items": items}

@router.get("/profile/{profile_id}")
async def get_profile_details(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed profile information.
    Handles both internal UUIDs and external PCIDs.
    """
    # 1. Try Internal First
    try:
        user = db.query(User).filter(User.id == int(profile_id) if profile_id.isdigit() else None).first()
        if user:
            return {
                "id": str(user.id),
                "name": user.full_name,
                "bio": user.bio,
                "image_url": f"https://ui-avatars.com/api/?name={user.full_name.replace(' ', '+')}&size=300",
                "location": user.location,
                "social_links": {"twitter": "#", "linkedin": "#"},
                "podcast_appearances": [],
                "type": "internal"
            }
    except:
        pass

    # 2. Try External
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{INGESTION_SERVICE_URL}/creator/{profile_id}")
            if response.status_code == 200:
                data = response.json()
                creator = data.get("creator", {})
                return {
                    "id": creator.get("pcid"),
                    "name": creator.get("name"),
                    "bio": creator.get("bio", ""),
                    "image_url": creator.get("imageUrl"),
                    "location": creator.get("location"),
                    "social_links": creator.get("socialLinks", {}),
                    "podcast_appearances": [],
                    "type": "external"
                }
    except Exception as e:
        logger.error(f"External profile fetch failed: {e}")

    raise HTTPException(status_code=404, detail="Profile not found")

@router.get("/search/podcasts")
async def search_podcasts(
    q: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """Search for podcasts via ingestion service."""
    if not httpx:
        return {"podcasts": [], "total": 0}
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{INGESTION_SERVICE_URL}/search/podcasts",
                params={"q": q, "limit": limit}
            )
            if response.status_code == 200:
                data = response.json()
                podcasts = data.get("podcasts", {}).get("data", [])
                results = []
                for p in podcasts:
                    results.append({
                        "id": p.get("id"),
                        "title": p.get("title"),
                        "description": p.get("description", ""),
                        "image_url": p.get("imageUrl"),
                        "rating": p.get("ratingAverage"),
                        "categories": [c.get("title") for c in p.get("categories", [])]
                    })
                return {"podcasts": results, "total": len(results)}
    except Exception as e:
        logger.error(f"Podcast search failed: {e}")
        
    return {"podcasts": [], "total": 0}

@router.get("/podcast/{podcast_id}")
async def get_podcast_details(
    podcast_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get podcast details via ingestion service."""
    if not httpx:
        raise HTTPException(status_code=503, detail="Discovery service offline")
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{INGESTION_SERVICE_URL}/podcast/{podcast_id}")
            if response.status_code == 200:
                data = response.json()
                podcast = data.get("podcast", {})
                return {
                    "id": podcast.get("id"),
                    "title": podcast.get("title"),
                    "description": podcast.get("description", ""),
                    "image_url": podcast.get("imageUrl"),
                    "rating": podcast.get("ratingAverage"),
                    "categories": [c.get("title") for c in podcast.get("categories", [])],
                    "type": "podcast"
                }
    except Exception as e:
        logger.error(f"Podcast fetch failed: {e}")
        
    raise HTTPException(status_code=404, detail="Podcast not found")
