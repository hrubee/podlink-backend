from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import redis
from app.services.matching import MatchingService
from app.services.payments import PaymentService
from app.api import deps, auth_deps
from app.models.safety import UserReport
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()

class LikeRequest(BaseModel):
    target_id: int

class ReportCreate(BaseModel):
    target_id: int
    reason: str
    details: str = None

class SearchQuery(BaseModel):
    q: str
    limit: int = 10

@router.get("/search")
async def semantic_search(
    q: str,
    limit: int = 10,
    current_user: User = Depends(auth_deps.get_current_user)
):
    """Proxy semantic search request to the ML service."""
    import httpx
    from app.core.config import settings
    ml_url = f"{settings.ML_SERVICE_URL}/search"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(ml_url, json={"query": q, "top_k": limit})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"ML service searches are currently unavailable: {e}")

@router.post("/like")
async def like_user(
    request: LikeRequest,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    payment_service = PaymentService(db, r)
    current_user_id = str(current_user.id)
    
    # Feature Gate: Check Quota/Premium status
    if not await payment_service.check_feature_access(current_user_id):
        raise HTTPException(status_code=402, detail="Outreach limit reached. Please upgrade to Premium.")

    service = MatchingService(db, r)
    is_match = await service.handle_like(current_user_id, request.target_id)
    
    # Increment quota usage for free users
    if not is_match: # Log only if it's an outreach attempt, or customize as needed
        await payment_service.increment_quota(current_user_id)
    
    return {
        "status": "success",
        "is_match": is_match,
        "message": "Match detected!" if is_match else "Like recorded"
    }

@router.post("/report")
async def submit_report(
    report: ReportCreate,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    new_report = UserReport(
        reporter_id=current_user.id,
        target_id=report.target_id,
        reason=report.reason,
        details=report.details
    )
    db.add(new_report)
    db.commit()
    return {"status": "success", "message": "Report submitted for review."}

@router.get("/feed")
async def get_recommendation_feed(
    limit: int = 20,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """
    Get a ranked feed of potential matches.
    Only shows users of the opposite role who haven't been liked/disliked yet.
    """
    from app.models.user import UserRole
    from app.models.matches import Interaction
    import httpx

    # 1. Determine target role
    target_role = UserRole.GUEST if current_user.role == UserRole.HOST else UserRole.HOST
    
    # 2. Get IDs of users already interacted with
    interacted_ids = db.query(Interaction.target_id).filter(
        Interaction.actor_id == str(current_user.id)
    ).all()
    interacted_ids = [str(i[0]) for i in interacted_ids]
    interacted_ids.append(str(current_user.id)) # Don't show self

    # 3. Fetch potential candidates
    candidates = db.query(User).filter(
        User.role == target_role,
        User.onboarded == True,
        User.is_public == True,
        ~User.id.in_(interacted_ids)
    ).limit(100).all()

    if not candidates:
        return {"profiles": []}

    # 4. Prepare data for ML Service
    ml_request_data = {
        "user_id": current_user.id,
        "user_metadata": {
            "topics": current_user.topics,
            "bio": current_user.bio,
            "target_audience": current_user.target_audience
        },
        "candidates": [
            {
                "id": c.id,
                "topics": c.topics,
                "bio": c.bio,
                "target_audience": c.target_audience
            } for c in candidates
        ]
    }

    # 5. Call ML Service for ranking
    from app.core.config import settings as _s
    ml_url = f"{_s.ML_SERVICE_URL}/rank"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(ml_url, json=ml_request_data, timeout=5.0)
            response.raise_for_status()
            ranking_data = response.json()
            ranked_ids = [int(rid) for rid in ranking_data.get("ranked_ids", [])]
    except Exception as e:
        print(f"ML Service error: {e}")
        # Fallback to simple random if ML is down
        ranked_ids = [c.id for c in candidates]

    # 6. Re-order candidates based on ML ranking and transform to profile format
    id_map = {c.id: c for c in candidates}
    sorted_profiles = []
    
    for rid in ranked_ids:
        if rid in id_map:
            u = id_map[rid]
            sorted_profiles.append({
                "id": u.id,
                "name": u.full_name,
                "bio": u.bio,
                "image_url": u.avatar_url,
                "subtitle": u.host_details.get("podcast_name") if u.role == UserRole.HOST else u.guest_details.get("expertise_areas"),
                "topics": u.topics,
                "type": u.role,
                "verified": True
            })

    return {"profiles": sorted_profiles[:limit]}

@router.get("/matches")
async def get_matches(
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    current_user_id = str(current_user.id)
    service = MatchingService(db, r)
    match_ids = await service.get_active_matches(current_user_id)
    return {"matches": match_ids}

@router.post("/unmatch")
async def unmatch_user(
    request: LikeRequest,
    current_user: User = Depends(auth_deps.get_current_user),
    db: Session = Depends(deps.get_db),
    r: redis.Redis = Depends(deps.get_redis)
):
    current_user_id = str(current_user.id)
    service = MatchingService(db, r)
    await service.unmatch(current_user_id, request.target_id)
    return {"status": "unmatched"}
