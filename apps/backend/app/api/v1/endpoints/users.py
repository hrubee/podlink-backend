from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps, auth_deps
from app.models.user import User, UserRole
from pydantic import BaseModel

router = APIRouter()

class OnboardingUpdate(BaseModel):
    full_name: Optional[str] = None
    role: UserRole
    bio: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    topics: List[str]
    target_audience: Optional[str] = None
    language: str = "English"
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
    This data is used for profile visibility and matching algorithms.
    """
    try:
        if data.full_name:
            current_user.full_name = data.full_name
        
        current_user.role = data.role
        current_user.bio = data.bio
        current_user.avatar_url = data.avatar_url
        current_user.location = data.location
        current_user.topics = data.topics
        current_user.target_audience = data.target_audience
        current_user.language = data.language
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
        "onboarded": current_user.onboarded,
        "topics": current_user.topics,
        "target_audience": current_user.target_audience,
        "language": current_user.language,
        "social_links": current_user.social_links,
        "host_details": current_user.host_details,
        "guest_details": current_user.guest_details,
    }

@router.get("/{user_id}/public", response_model=dict)
def get_public_profile(
    user_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Publicly accessible profile information.
    """
    user = db.query(User).filter(User.id == user_id, User.is_public == True, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found or is private")
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "location": user.location,
        "topics": user.topics,
        "target_audience": user.target_audience,
        "language": user.language,
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
