from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.api import deps, auth_deps
from app.models.user import User, UserRole
from pydantic import BaseModel

router = APIRouter()


class OnboardingUpdate(BaseModel):
    # Core
    full_name: Optional[str] = None
    role: UserRole
    bio: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None

    # Matching signals
    topics: List[str]
    target_audience: Optional[str] = None
    language: str = "English"
    engagement_style: List[str] = []

    # Format preferences
    interview_format: str = "both"
    episode_length_pref: str = "45-60"
    content_rating: str = "clean"
    fee_expectation: str = "free"

    # Role-specific & social
    social_links: dict = {}
    host_details: dict = {}
    guest_details: dict = {}


class UserUpdate(BaseModel):
    """Allow partial updates for profile editing"""
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    
    topics: Optional[List[str]] = None
    target_audience: Optional[str] = None
    language: Optional[str] = None
    engagement_style: Optional[List[str]] = None
    
    interview_format: Optional[str] = None
    episode_length_pref: Optional[str] = None
    content_rating: Optional[str] = None
    fee_expectation: Optional[str] = None
    
    social_links: Optional[Dict] = None
    host_details: Optional[Dict] = None
    guest_details: Optional[Dict] = None


@router.post("/onboarding", response_model=dict)
def submit_onboarding(
    data: OnboardingUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Submits onboarding data for a user.
    All fields are used by the AI matching engine for content-based scoring.
    Also triggers a background task to add this user to the ML vector index.
    """
    try:
        if data.full_name:
            current_user.full_name = data.full_name

        current_user.role = data.role
        current_user.bio = data.bio
        current_user.avatar_url = data.avatar_url
        current_user.location = data.location
        current_user.timezone = data.timezone

        # Matching signals
        current_user.topics = data.topics
        current_user.target_audience = data.target_audience
        current_user.language = data.language
        current_user.engagement_style = data.engagement_style

        # Format preferences
        current_user.interview_format = data.interview_format
        current_user.episode_length_pref = data.episode_length_pref
        current_user.content_rating = data.content_rating
        current_user.fee_expectation = data.fee_expectation

        # Role-specific & social
        current_user.social_links = data.social_links
        current_user.host_details = data.host_details
        current_user.guest_details = data.guest_details

        current_user.onboarded = True

        db.commit()
        db.refresh(current_user)

        # Asynchronously add this user to the ML vector index
        background_tasks.add_task(_index_user_in_ml, current_user)

        return {"status": "success", "message": "Onboarding completed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save onboarding data: {str(e)}")


async def _index_user_in_ml(user: User):
    """Background task: add or update a user's profile in the ML vector index."""
    import httpx
    import logging
    from app.core.config import settings
    if not settings.ML_SERVICE_URL:
        return
    payload = {
        "id": user.id,
        "bio": user.bio or "",
        "topics": user.topics or [],
        "target_audience": user.target_audience or "",
        "language": user.language or "English",
        "engagement_style": user.engagement_style or [],
        "interview_format": user.interview_format or "both",
        "episode_length_pref": user.episode_length_pref or "45-60",
        "content_rating": user.content_rating or "clean",
        "fee_expectation": user.fee_expectation or "free",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/index/add",
                json=payload,
                timeout=10.0
            )
            logging.getLogger(__name__).info(
                f"ML index updated for user {user.id}: {resp.status_code}"
            )
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"ML index update failed for user {user.id}: {e}"
        )


@router.put("/me", response_model=dict)
def update_user_me(
    data: UserUpdate,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Update current user profile (partial update)"""
    try:
        # Update only fields that are provided (not None)
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(current_user, field, value)

        db.commit()
        db.refresh(current_user)
        return {"status": "success", "message": "Profile updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.get("/me", response_model=dict)
def get_my_profile(
    current_user: User = Depends(auth_deps.get_current_user)
) -> Any:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "location": current_user.location,
        "timezone": current_user.timezone,
        "onboarded": current_user.onboarded,
        "topics": current_user.topics,
        "target_audience": current_user.target_audience,
        "language": current_user.language,
        "engagement_style": current_user.engagement_style,
        "interview_format": current_user.interview_format,
        "episode_length_pref": current_user.episode_length_pref,
        "content_rating": current_user.content_rating,
        "fee_expectation": current_user.fee_expectation,
        "social_links": current_user.social_links,
        "host_details": current_user.host_details,
        "guest_details": current_user.guest_details,
    }


@router.get("/{user_id}/public", response_model=dict)
def get_public_profile(
    user_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """Publicly accessible profile information."""
    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "location": user.location,
        "timezone": user.timezone,
        "topics": user.topics,
        "target_audience": user.target_audience,
        "language": user.language,
        "engagement_style": user.engagement_style,
        "interview_format": user.interview_format,
        "episode_length_pref": user.episode_length_pref,
        "content_rating": user.content_rating,
        "fee_expectation": user.fee_expectation,
        "social_links": user.social_links,
        "host_details": user.host_details if user.role == UserRole.HOST else {},
        "guest_details": user.guest_details if user.role == UserRole.GUEST else {},
        "podcasts": [
            {
                "id": p.id,
                "title": p.title,
                "cover_image": p.cover_image,
                "slug": p.slug
            } for p in user.podcasts
        ] if user.podcasts else [],
        "created_at": user.created_at
    }
