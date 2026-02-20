from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.api import deps, auth_deps
from app.models.podcast import Podcast, PodcastHost
from app.models.user import User

router = APIRouter()

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class PodcastBase(BaseModel):
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    website_url: Optional[str] = None
    rss_feed_url: Optional[str] = None
    topics: List[str] = []
    category: Optional[str] = None
    language: str = "English"
    monthly_listeners: Optional[str] = None

class PodcastCreate(PodcastBase):
    pass

class PodcastResponse(PodcastBase):
    id: int
    slug: Optional[str] = None
    
    class Config:
        orm_mode = True

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PodcastResponse])
def get_podcasts(
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(deps.get_db)
):
    """List all podcasts publicly."""
    podcasts = db.query(Podcast).offset(skip).limit(limit).all()
    return podcasts

@router.get("/{id}", response_model=PodcastResponse)
def get_podcast(id: int, db: Session = Depends(deps.get_db)):
    """Get podcast details by ID."""
    podcast = db.query(Podcast).filter(Podcast.id == id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return podcast

@router.post("/", response_model=PodcastResponse)
def create_podcast(
    podcast_in: PodcastCreate, 
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(auth_deps.get_current_user)
):
    """Create a new podcast and link the creator as the primary host."""
    
    # 1. Create Podcast
    new_podcast = Podcast(
        title=podcast_in.title,
        description=podcast_in.description,
        cover_image=podcast_in.cover_image,
        website_url=podcast_in.website_url,
        rss_feed_url=podcast_in.rss_feed_url,
        topics=podcast_in.topics,
        category=podcast_in.category,
        language=podcast_in.language,
        monthly_listeners=podcast_in.monthly_listeners
    )
    db.add(new_podcast)
    db.commit()
    db.refresh(new_podcast)
    
    # 2. Link User as Host
    link = PodcastHost(
        podcast_id=new_podcast.id,
        user_id=current_user.id,
        role="host",
        is_primary=True
    )
    db.add(link)
    db.commit()
    
    return new_podcast

@router.post("/{podcast_id}/claim", status_code=status.HTTP_201_CREATED)
def claim_podcast(
    podcast_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(auth_deps.get_current_user)
):
    """Link an existing podcast to the current user."""
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
        
    existing_link = db.query(PodcastHost).filter(
        PodcastHost.podcast_id == podcast_id,
        PodcastHost.user_id == current_user.id
    ).first()
    
    if existing_link:
        return {"message": "Already linked to this podcast"}
        
    link = PodcastHost(
        podcast_id=podcast_id,
        user_id=current_user.id,
        role="host",
        is_primary=False 
    )
    db.add(link)
    db.commit()
    
    return {"message": "Podcast linked successfully"}
