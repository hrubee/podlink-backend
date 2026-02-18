from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
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


@router.post("/onboarding", response_model=dict)
def submit_onboarding(
    data: OnboardingUpdate,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Submits onboarding data for a user.
    All fields are used by the AI matching engine for content-based scoring.
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

        return {"status": "success", "message": "Onboarding completed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save onboarding data: {str(e)}")


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
        User.is_public == True,
        User.is_active == True
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found or is private")

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
        "managed_by": {
            "id": user.managed_by_agency.id,
            "name": user.managed_by_agency.name,
            "slug": user.managed_by_agency.slug
        } if user.managed_by_agency else None,
        "created_at": user.created_at
    }
