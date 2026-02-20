from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import logging

from app.api.auth_deps import get_current_user
from app.api.deps import get_db
from app.models.user import User
from app.models.podcast import Podcast

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/search/profiles")
async def search_profiles(
    q: str,
    type: Optional[str] = None,  # "host", "guest", or None for both
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for podcast hosts and guests directly from the internal database.
    """
    profiles = []
    
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
                "subtitle": f"{'Host' if u.role == 'HOST' else 'Guest'} • {u.location or 'Global'}",
                "topics": u.topics or [],
                "type": "internal"
            })
    except Exception as e:
        logger.error(f"Local profile search failed: {e}")

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
    Discover trending podcasts internally.
    """
    items = []
    try:
        podcasts = db.query(Podcast).limit(limit).all()
        for p in podcasts:
            items.append({
                "id": str(p.id),
                "title": p.title,
                "description": p.description or "",
                "image_url": p.cover_image or f"https://ui-avatars.com/api/?name={p.title.replace(' ', '+')}&size=200&background=6366f1&color=fff",
                "categories": p.topics[:3] if p.topics else ["Podcast"],
                "type": "podcast"
            })
            
        # Fallback to featuring active hosts
        if len(items) < limit:
            featured = db.query(User).filter(User.role == "HOST", User.onboarded == True).limit(limit - len(items)).all()
            for u in featured:
                items.append({
                    "id": str(u.id),
                    "title": u.host_details.get("podcast_name", f"{u.full_name}'s Podcast") if u.host_details else f"{u.full_name}'s Podcast",
                    "description": u.bio or "",
                    "image_url": f"https://ui-avatars.com/api/?name={u.full_name.replace(' ', '+')}&size=200&background=6366f1&color=fff",
                    "categories": u.topics[:3] if u.topics else ["Podcast"],
                    "type": "featured_profile"
                })
    except Exception as e:
        logger.error(f"Internal trending search failed: {e}")

    return {"items": items}

@router.get("/profile/{profile_id}")
async def get_profile_details(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed profile information from internal DB.
    """
    try:
        user = db.query(User).filter(User.id == int(profile_id) if profile_id.isdigit() else None).first()
        if user:
            safe_name = user.full_name.replace(' ', '+') if user.full_name else "User"
            return {
                "id": str(user.id),
                "name": user.full_name,
                "bio": user.bio,
                "image_url": user.avatar_url or f"https://ui-avatars.com/api/?name={safe_name}&size=300",
                "location": user.location,
                "social_links": user.social_links or {},
                "podcast_appearances": [],
                "type": "internal"
            }
    except Exception as e:
        logger.error(f"Profile fetch failed: {e}")

    raise HTTPException(status_code=404, detail="Profile not found")

@router.get("/search/podcasts")
async def search_podcasts(
    q: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for podcasts internally."""
    results = []
    try:
        query = db.query(Podcast).filter(
            or_(
                Podcast.title.ilike(f"%{q}%"),
                Podcast.description.ilike(f"%{q}%"),
                Podcast.topics.cast(str).ilike(f"%{q}%")
            )
        )
        podcasts = query.limit(limit).all()
        for p in podcasts:
            results.append({
                "id": str(p.id),
                "title": p.title,
                "description": p.description or "",
                "image_url": p.cover_image or f"https://ui-avatars.com/api/?name={p.title.replace(' ', '+')}&size=200&background=6366f1&color=fff",
                "categories": p.topics[:3] if p.topics else ["Podcast"]
            })
    except Exception as e:
        logger.error(f"Podcast search failed: {e}")
        
    return {"podcasts": results, "total": len(results)}

@router.get("/podcast/{podcast_id}")
async def get_podcast_details(
    podcast_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get podcast details internally."""
    try:
        podcast = db.query(Podcast).filter(Podcast.id == int(podcast_id) if podcast_id.isdigit() else None).first()
        if podcast:
            return {
                "id": str(podcast.id),
                "title": podcast.title,
                "description": podcast.description or "",
                "image_url": podcast.cover_image or f"https://ui-avatars.com/api/?name={podcast.title.replace(' ', '+')}&size=200&background=6366f1&color=fff",
                "categories": podcast.topics[:3] if podcast.topics else ["Podcast"],
                "type": "podcast",
                "website_url": podcast.website_url,
                "rss_feed_url": podcast.rss_feed_url
            }
    except Exception as e:
        logger.error(f"Podcast fetch failed: {e}")
        
    raise HTTPException(status_code=404, detail="Podcast not found")
